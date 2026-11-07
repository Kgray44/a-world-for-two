package worldfortwo.living;

import com.google.gson.*;
import java.time.*;
import java.util.*;

/** Bounded accounting for admitted requests and metadata actually returned by upstream. */
public final class NativeUsage {
    public static final int MAX_LEDGER_BYTES=256*1024;
    private NativeUsage(){}
    private static int bounded(JsonObject object,String key,int fallback,int high){return Math.max(1,Math.min(high,WorldCharacters.integer(object,key,fallback)));}
    private static long count(JsonObject object,String key){try{long value=object.get(key).getAsLong();if(value>=0)return value;}catch(Exception ignored){}return 0;}
    private static double amount(JsonObject object,String key){try{double value=object.get(key).getAsDouble();if(Double.isFinite(value)&&value>=0)return value;}catch(Exception ignored){}return 0;}
    private static double reserved(JsonObject ledger){
        return reserved(ledger,"reserved_usd");
    }
    private static double reserved(JsonObject ledger,String key){
        if(!ledger.has(key))return 0;
        double value=ledger.get(key).getAsDouble();
        if(!Double.isFinite(value)||value<0)throw new IllegalStateException("Existing reservation is invalid");return value;
    }
    private static long admitted(JsonObject ledger){
        return admitted(ledger,"day_requests");
    }
    private static long admitted(JsonObject ledger,String key){
        if(!ledger.has(key))return 0;
        double value=ledger.get(key).getAsDouble();
        if(!Double.isFinite(value)||value<0||value!=Math.rint(value)||value>1000000)throw new IllegalStateException("Existing admission count is invalid");return (long)value;
    }
    public static JsonObject reserve(JsonObject ledger,NativeRequestPolicy.Policy policy,JsonObject settings,JsonObject ai,String character,long now,int inputBound){
        if(ledger.has("format")&&!WorldCharacters.text(ledger,"format").equals("awft-native-ai-usage:2"))throw new IllegalStateException("Unrecognized spending ledger");
        String day=Instant.ofEpochMilli(now).atZone(ZoneOffset.UTC).toLocalDate().toString();
        int perDay=bounded(settings,"requests_per_day",100,1000);
        boolean same=day.equals(WorldCharacters.text(ledger,"day"));
        double charged=same?reserved(ledger):0;
        // Old positive reservations do not establish a complete daily request count.
        if(same&&charged>0&&!ledger.has("day_requests"))throw new IllegalStateException("Old daily admission count is unknown");
        long daily=same?admitted(ledger):0;
        boolean previewToday=day.equals(WorldCharacters.text(ledger,"preview_day"));
        double previewCharge=previewToday?reserved(ledger,"preview_reserved_usd"):0;
        if(previewCharge>0&&!ledger.has("preview_day_requests"))throw new IllegalStateException("Old preview admission count is unknown");
        long previewCount=previewToday?admitted(ledger,"preview_day_requests"):0;
        if(daily+previewCount>=perDay)throw new IllegalStateException("Combined daily AI admission limit reached");
        double budget=amount(settings,"daily_budget_usd");
        double cost=(Math.max(0,inputBound)*policy.inputRate()+policy.responseTokens()*policy.outputRate())/1000000.0;
        if(!(budget>0)||!Double.isFinite(cost)||charged+previewCharge+cost>budget)throw new IllegalStateException("Combined daily reserved allowance reached");
        JsonArray recent=new JsonArray();int minute=0,hour=0,individual=0;long latest=0;
        for(JsonElement entry:WorldCharacters.array(ledger,"requests")){
            JsonObject row=entry.getAsJsonObject();long at=row.get("at").getAsLong();
            if(at>now+2000)throw new IllegalStateException("Admission clock differs");
            if(now-at>=86400000L)continue;
            recent.add(row);
            if(now-at<60000)minute++;
            if(now-at<3600000L){hour++;if(character.equals(WorldCharacters.text(row,"character"))){individual++;latest=Math.max(latest,at);}}
        }
        for(JsonElement entry:WorldCharacters.array(ledger,"preview_recent")){
            JsonObject row=entry.getAsJsonObject();long at=row.get("at").getAsLong();
            if(at>now+2000)throw new IllegalStateException("Preview admission clock differs");
            if(now-at<60000)minute++;
            if(now-at<3600000L){hour++;if(character.equals(WorldCharacters.text(row,"character"))){individual++;latest=Math.max(latest,at);}}
        }
        if(minute>=bounded(settings,"requests_per_minute",6,60)||hour>=bounded(settings,"requests_per_hour",24,60)
                ||individual>=bounded(ai,"requests_per_hour",12,60)
                ||latest>0&&now-latest<Math.max(5,WorldCharacters.integer(ai,"cooldown_seconds",20))*1000L)
            throw new IllegalStateException("AI rate or cooldown limit reached");
        if(!same){ledger.addProperty("day_dispatched",0);ledger.add("day_usage",new JsonObject());ledger.addProperty("day_estimated_token_cost_usd",0);}
        JsonObject attempt=new JsonObject();attempt.addProperty("id",policy.capture().id());attempt.addProperty("character",character);
        attempt.addProperty("at",now);attempt.addProperty("day",day);attempt.addProperty("requested_model",policy.model());attempt.add("model",JsonNull.INSTANCE);
        attempt.addProperty("reasoning_effort",policy.reasoningEffort());attempt.addProperty("response_tokens",policy.responseTokens());
        attempt.addProperty("reserved_usd",cost);attempt.addProperty("input_usd_per_million",policy.inputRate());attempt.addProperty("output_usd_per_million",policy.outputRate());
        attempt.addProperty("status","reserved");attempt.addProperty("usage_available",false);attempt.addProperty("dispatched",false);recent.add(attempt);
        while(recent.size()>128)recent.remove(0);
        ledger.addProperty("format","awft-native-ai-usage:2");ledger.addProperty("day",day);ledger.addProperty("reserved_usd",charged+cost);
        ledger.addProperty("day_requests",daily+1);ledger.add("requests",recent);
        return attempt;
    }
    public static void finish(JsonObject ledger,String id,JsonObject observed){
        for(JsonElement item:WorldCharacters.array(ledger,"requests")){
            JsonObject row=item.getAsJsonObject();if(!id.equals(WorldCharacters.text(row,"id")))continue;
            boolean today=WorldCharacters.text(row,"day").equals(WorldCharacters.text(ledger,"day"));
            if(today&&!WorldCharacters.flag(row,"dispatched")&&WorldCharacters.flag(observed,"dispatched"))ledger.addProperty("day_dispatched",count(ledger,"day_dispatched")+1);
            for(var field:observed.entrySet())row.add(field.getKey(),field.getValue().deepCopy());
            if(today&&WorldCharacters.flag(row,"usage_available")&&!WorldCharacters.flag(row,"usage_counted")){
                JsonObject usage=WorldCharacters.object(row,"usage"),totals=WorldCharacters.object(ledger,"day_usage");
                for(String key:List.of("prompt_tokens","completion_tokens","total_tokens","cached_tokens","reasoning_tokens"))
                    if(usage.has(key))totals.addProperty(key,count(totals,key)+count(usage,key));
                ledger.add("day_usage",totals);
                double estimated=(count(usage,"prompt_tokens")*amount(row,"input_usd_per_million")+count(usage,"completion_tokens")*amount(row,"output_usd_per_million"))/1000000.0;
                row.addProperty("estimated_token_cost_usd",estimated);row.addProperty("usage_counted",true);
                ledger.addProperty("day_estimated_token_cost_usd",amount(ledger,"day_estimated_token_cost_usd")+estimated);
            }
            return;
        }
    }
}
