package worldfortwo.bridge;

import java.util.List;
import net.minecraft.core.Registry;
import net.minecraft.world.level.dimension.LevelStem;

/** Private per-attempt cache custody; required redirects never publish partial native loads. */
public final class LithostitchedSeedgenLoadScope implements AutoCloseable {
    private static final ThreadLocal<LithostitchedSeedgenLoadScope> CURRENT=new ThreadLocal<>();
    private Registry<LevelStem> stems;private List<String> names;
    private boolean wroteStems,wroteNames;
    private LithostitchedSeedgenLoadScope(){}
    public static LithostitchedSeedgenLoadScope enter() {
        if(CURRENT.get()!=null)throw new IllegalStateException("Reentrant native terrain attempt");
        var frame=new LithostitchedSeedgenLoadScope();CURRENT.set(frame);return frame;
    }
    public static LithostitchedSeedgenLoadScope current() {
        var frame=CURRENT.get();if(frame==null)throw new IllegalStateException("Required native attempt scope is absent");return frame;
    }
    public static void writeStems(Registry<LevelStem> value) {
        var frame=current();if(frame.wroteStems)throw new IllegalStateException("Native stem write topology changed");
        frame.stems=java.util.Objects.requireNonNull(value);frame.wroteStems=true;
    }
    public static void writeNames(List<String> value) {
        var frame=current();if(frame.wroteNames||value==null||value.size()>256)throw new IllegalStateException("Native pack-name write topology changed");
        frame.names=List.copyOf(value);frame.wroteNames=true;
    }
    public static Registry<LevelStem> readStems() {
        var frame=current();if(!frame.wroteStems)throw new IllegalStateException("Native attempt read stems before its scoped write");return frame.stems;
    }
    public Registry<LevelStem> stems(){requireComplete();return stems;}
    public List<String> names(){requireComplete();return names;}
    public void requireComplete(){if(!wroteStems||!wroteNames)throw new IllegalStateException("Native attempt did not provide complete cache fields");}
    @Override public void close() {
        if(CURRENT.get()!=this)throw new IllegalStateException("Native attempt scope ownership changed");CURRENT.remove();
    }
}
