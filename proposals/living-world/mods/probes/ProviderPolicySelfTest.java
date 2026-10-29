import com.google.gson.*;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfoReturnable;
import tn.naizo.smartvillagers.config.SmartVillagersConfig;
import worldfortwo.living.WorldCharacters;
import worldfortwo.living.NativeRequestPolicy;

/** Executes the actual policy callback; does not apply Mixins or start Minecraft. */
public final class ProviderPolicySelfTest {
    private static SmartVillagersConfig.Snapshot policy(JsonObject settings)throws Exception{
        JsonObject document=new JsonObject();document.add("settings",settings);
        WorldCharacters.current=new WorldCharacters(document);
        var callback=new CallbackInfoReturnable<SmartVillagersConfig.Snapshot>("fixture",true,SmartVillagersConfig.Snapshot.defaults());
        var method=Class.forName("worldfortwo.living.mixin.ProviderConfigMixin").getDeclaredMethod("awft$settings",CallbackInfoReturnable.class);
        method.setAccessible(true);method.invoke(null,callback);return callback.getReturnValue();
    }
    private static void require(boolean value){if(!value)throw new AssertionError("Provider policy differs");}
    public static void main(String[] args)throws Exception{
        JsonObject settings=new JsonObject();settings.addProperty("external_enabled",false);
        settings.addProperty("provider","openai");settings.addProperty("model","fixture-model");settings.addProperty("max_concurrent",100);
        var disabled=policy(settings);require(disabled.model().isBlank());
        settings.addProperty("external_enabled",true);require(policy(settings).model().isBlank());
        settings.addProperty("endpoint",NativeRequestPolicy.ENDPOINT);settings.addProperty("reasoning_effort","none");settings.addProperty("response_tokens",120);
        JsonObject document=new JsonObject();document.add("settings",settings);
        JsonObject verification=JsonParser.parseString("""
            {"verified":true,"model":"fixture-model","endpoint":"https://api.openai.com/v1/chat/completions",
             "reasoning_effort":"none","response_tokens":120,"model_policies":{"fixture-model":{
               "verified":true,"model":"fixture-model","endpoint":"https://api.openai.com/v1/chat/completions",
               "reasoning_supported":false,"reasoning_efforts":["none"],"temperature_supported":false,
               "input_usd_per_million":1,"output_usd_per_million":1}}}
            """).getAsJsonObject();document.add("provider_verification",verification);
        WorldCharacters.current=new WorldCharacters(document);
        var activeCallback=new CallbackInfoReturnable<SmartVillagersConfig.Snapshot>("fixture",true,SmartVillagersConfig.Snapshot.defaults());
        var callback=Class.forName("worldfortwo.living.mixin.ProviderConfigMixin").getDeclaredMethod("awft$settings",CallbackInfoReturnable.class);
        callback.setAccessible(true);callback.invoke(null,activeCallback);var active=activeCallback.getReturnValue();
        require(active.model().equals("fixture-model")&&active.provider().name().equals("OPENAI"));
        require(active.apiBaseUrl().equals("https://api.openai.com/v1/chat/completions"));
        require(active.maxConcurrent()==2&&active.maxTokens()==120&&active.requirePlayerOptIn()&&active.requirePrefix());
        require(!active.voiceEnabled()&&!active.requestsEnabled()&&active.speechBubbles());
        var bodyCallback=new CallbackInfoReturnable<String>("fixture",true,"{\"model\":\"incorrect\",\"messages\":[]}");
        var parameters=Class.forName("worldfortwo.living.mixin.NativeTransportMixin").getDeclaredMethod("awft$parameters",SmartVillagersConfig.Snapshot.class,String.class,String.class,CallbackInfoReturnable.class);
        parameters.setAccessible(true);
        try(var scope=NativeRequestPolicy.enter(NativeRequestPolicy.select(WorldCharacters.current,null))){parameters.invoke(null,active,"system","user",bodyCallback);}
        var body=JsonParser.parseString(bodyCallback.getReturnValue()).getAsJsonObject();
        require(body.get("model").getAsString().equals("fixture-model")&&body.get("max_completion_tokens").getAsInt()==120&&!body.has("reasoning_effort")&&!body.has("temperature"));
        settings.addProperty("provider","anthropic");require(policy(settings).model().isBlank());
        System.out.println("Actual provider policy callback passed; no Mixin transformation, game or network request performed.");
    }
}
