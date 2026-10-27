package worldfortwo.bridge;

import java.lang.invoke.MethodHandle;
import java.lang.invoke.MethodHandles;
import java.time.Instant;
import java.util.LinkedHashMap;
import java.util.Map;
import net.minecraft.server.level.ServerLevel;
import net.neoforged.neoforge.common.world.chunk.ForcedChunkManager;

/** Original read-only native idle telemetry. No world or simulation mutation.
 * Mirrors only the pinned NeoForge 21.1.262 empty-world branch. Holder ticking
 * ranges and this branch's eligibility are not proof a particular BE tick ran.
 */
public final class IdleSimulationState {
    private IdleSimulationState() {}
    private record Binding(MethodHandle getter,String unavailable) {}
    private static final class CounterBinding {
        static final Binding VALUE=bind();
        private static Binding bind() {
            try {
                var lookup=MethodHandles.privateLookupIn(ServerLevel.class,MethodHandles.lookup());
                return new Binding(lookup.findGetter(ServerLevel.class,"emptyTime",int.class),null);
            } catch(Throwable failure) {
                if(failure instanceof VirtualMachineError || failure instanceof ThreadDeath)throw (Error)failure;
                return new Binding(null,failure.getClass().getName());
            }
        }
    }

    public static Map<String,Object> sample(ServerLevel level) {
        if(level==null || level.getServer()==null || !level.getServer().isSameThread())
            return Map.of("status","unavailable","reason","Collect only on the actual server thread");
        Map<String,Object> row=new LinkedHashMap<>();
        row.put("at",Instant.now().toString());row.put("dimension",level.dimension().location().toString());
        row.put("scope","Next native empty-world branch if this dimension ticks normally and inputs remain unchanged; no individual entity/BE progress measurement");
        row.put("idle_cutoff_ticks",300);row.put("simulation_wake_performed",false);
        int players=level.players().size();row.put("dimension_players",players);
        Boolean forced=null;
        try { forced=ForcedChunkManager.hasForcedChunks(level);row.put("native_saved_forced_chunk_branch",forced); }
        catch(Throwable failure) {
            if(failure instanceof VirtualMachineError || failure instanceof ThreadDeath)throw (Error)failure;
            row.put("native_forced_branch_unavailable",failure.getClass().getName());
        }
        Integer counter=null;Binding binding=CounterBinding.VALUE;
        if(binding.getter!=null) {
            try { counter=(int)binding.getter.invokeExact(level);row.put("empty_time_ticks",counter); }
            catch(Throwable failure) {
                if(failure instanceof VirtualMachineError || failure instanceof ThreadDeath)throw (Error)failure;
                row.put("counter_unavailable",failure.getClass().getName());
            }
        } else row.put("counter_unavailable",binding.unavailable);
        // A positive native player/forced branch is decisive even if reflective
        // counter access is unavailable. Unknown is never represented as zero.
        row.put("next_entity_and_block_entity_idle_branch",eligibility(players,forced,counter));
        row.put("status",counter!=null && forced!=null?"native_inputs_observed":"partial_native_inputs");
        row.put("note","Post-tick emptyTime=300 may follow the last eligible tick; this is next-branch eligibility, not a retrospective tick count. Loaded holders and distance-manager ranges remain separate.");
        return row;
    }

    // Package-visible pure branch for pinned-bytecode boundary fixtures.
    static String eligibility(int players,Boolean forced,Integer counter) {
        if(players<0)throw new IllegalArgumentException("Native player count cannot be negative");
        if(players>0 || Boolean.TRUE.equals(forced))return "eligible";
        if(forced==null || counter==null)return "unknown";
        return counter<300?"eligible":"suspended";
    }
}
