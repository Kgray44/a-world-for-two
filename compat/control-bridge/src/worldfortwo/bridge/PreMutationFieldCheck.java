package worldfortwo.bridge;

import java.util.Map;
import java.util.Objects;
import java.util.function.Consumer;
import java.util.function.Function;

/** Original synchronous full-state check. No setter, restore, tick or flag API. */
public final class PreMutationFieldCheck {
    private PreMutationFieldCheck() {}
    public record Drift<K,V>(K position,V expected,V actual,int checkedCells) {}
    public static final class DriftDetected extends IllegalStateException {
        public DriftDetected(Object position) {super("Complete tree preimage changed before owned mutation at "+position);}
    }
    public static <K,V> int requireUnchanged(Map<K,V> before,Function<K,V> actual,
                                           Consumer<Drift<K,V>> refusal) {
        Objects.requireNonNull(before);Objects.requireNonNull(actual);Objects.requireNonNull(refusal);
        if(before.isEmpty()||before.size()>131072)throw new IllegalArgumentException("One finite complete native field required");
        int checked=0;
        for(var row:before.entrySet()) {
            K position=Objects.requireNonNull(row.getKey());V expected=Objects.requireNonNull(row.getValue());
            V observed=actual.apply(position);checked++;
            if(observed==null||!expected.equals(observed)) {
                refusal.accept(new Drift<>(position,expected,observed,checked));
                throw new DriftDetected(position);
            }
        }
        return checked;
    }
}
