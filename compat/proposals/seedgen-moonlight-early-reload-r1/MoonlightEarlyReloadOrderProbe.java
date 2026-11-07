package worldfortwo.bridge;

import java.io.IOException;
import java.lang.reflect.Proxy;
import java.util.List;
import net.minecraft.server.packs.PackResources;

/** Offline identity/order fixtures only; never invokes the native reload. */
public final class MoonlightEarlyReloadOrderProbe {
    public static void main(String[] args)throws Exception {
        PackResources a=pack(),b=pack();
        MoonlightSeedgenEarlyReload.samePacks(List.of(a,b),List.of(a,b));
        refused(List.of(a,b),List.of(b,a));
        refused(List.of(a),List.of(a,b));
        refused(List.of(a),List.of(pack()));
        MoonlightSeedgenEarlyReload.prepare(false,null,null);
        System.out.println("PASS exact identity/order, count, substitute refusal and no-mod inactive path; no native lifecycle/world/cache action");
    }
    private static PackResources pack() {
        return (PackResources)Proxy.newProxyInstance(PackResources.class.getClassLoader(),
            new Class<?>[]{PackResources.class},(p,m,a)->{throw new AssertionError("No provider method may be invoked by identity fixture");});
    }
    private static void refused(List<PackResources> a,List<PackResources> b)throws IOException {
        try{MoonlightSeedgenEarlyReload.samePacks(a,b);}
        catch(IOException expected){return;}
        throw new AssertionError("Changed selected packs must be refused");
    }
}
