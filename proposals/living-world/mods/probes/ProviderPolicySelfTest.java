import com.google.gson.*;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfoReturnable;
import tn.naizo.smartvillagers.config.SmartVillagersConfig;
import worldfortwo.living.WorldCharacters;

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
        settings.addProperty("external_enabled",true);var active=policy(settings);
        require(active.model().equals("fixture-model")&&active.provider().name().equals("OPENAI"));
        require(active.apiBaseUrl().equals("https://api.openai.com/v1/chat/completions"));
        require(active.maxConcurrent()==2&&active.maxTokens()==120&&active.requirePlayerOptIn()&&active.requirePrefix());
        require(!active.voiceEnabled()&&!active.requestsEnabled()&&active.speechBubbles());
        settings.addProperty("provider","anthropic");require(policy(settings).model().isBlank());
        System.out.println("Actual provider policy callback passed; no Mixin transformation, game or network request performed.");
    }
}
