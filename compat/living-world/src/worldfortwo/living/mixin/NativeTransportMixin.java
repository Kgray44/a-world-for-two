package worldfortwo.living.mixin;

import java.net.http.*;
import java.time.Duration;
import java.util.concurrent.CompletableFuture;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.injection.*;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfoReturnable;
import tn.naizo.smartvillagers.ai.OpenAiCompatibleProvider;
import tn.naizo.smartvillagers.config.SmartVillagersConfig;
import worldfortwo.living.NativeRequestPolicy;

/** Reuse the author's transport; request metadata travels with its existing future. */
@Mixin(value=OpenAiCompatibleProvider.class,remap=false)
public abstract class NativeTransportMixin {
    @ModifyVariable(method="send",at=@At("HEAD"),argsOnly=true,ordinal=0,remap=false)
    private static String awft$dedicatedCredential(String ignored){return NativeRequestPolicy.current()==null?"":NativeRequestPolicy.dedicatedKey();}

    @Inject(method="buildRequestBody",at=@At("RETURN"),cancellable=true,remap=false)
    private static void awft$parameters(SmartVillagersConfig.Snapshot config,String system,String user,CallbackInfoReturnable<String> info){
        info.setReturnValue(NativeRequestPolicy.applyBody(info.getReturnValue()));
    }
    @Redirect(method="send",at=@At(value="INVOKE",target="Ljava/net/http/HttpRequest$Builder;timeout(Ljava/time/Duration;)Ljava/net/http/HttpRequest$Builder;",remap=false),remap=false)
    private static HttpRequest.Builder awft$timeout(HttpRequest.Builder builder,Duration original){
        var policy=NativeRequestPolicy.current();return builder.timeout(policy==null?original:Duration.ofSeconds(policy.timeoutSeconds()));
    }
    @Redirect(method="send",at=@At(value="INVOKE",target="Ljava/net/http/HttpClient;sendAsync(Ljava/net/http/HttpRequest;Ljava/net/http/HttpResponse$BodyHandler;)Ljava/util/concurrent/CompletableFuture;",remap=false),remap=false)
    private static CompletableFuture<HttpResponse<String>> awft$usage(HttpClient client,HttpRequest request,HttpResponse.BodyHandler<String> handler){
        var policy=NativeRequestPolicy.current();
        if(policy==null||!NativeRequestPolicy.credentialPresent()||!NativeRequestPolicy.ENDPOINT.equals(request.uri().toString()))
            return CompletableFuture.failedFuture(new IllegalStateException("Verified character transport context required"));
        var upstream=client.sendAsync(request,handler);policy.capture().dispatched();
        return upstream.thenApply(response->{policy.capture().observe(response.statusCode(),response.body());return response;});
    }
}
