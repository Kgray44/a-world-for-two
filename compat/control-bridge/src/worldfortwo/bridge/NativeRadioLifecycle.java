package worldfortwo.bridge;

import com.google.gson.JsonArray;
import com.google.gson.JsonElement;
import com.google.gson.JsonObject;
import com.simibubi.create.Create;
import com.simibubi.create.content.redstone.link.IRedstoneLinkable;
import com.simibubi.create.content.redstone.link.LinkBehaviour;
import com.simibubi.create.content.redstone.link.RedstoneLinkBlock;
import com.simibubi.create.content.redstone.link.RedstoneLinkBlockEntity;
import com.simibubi.create.content.redstone.link.RedstoneLinkNetworkHandler;
import net.minecraft.core.BlockPos;
import net.minecraft.core.Direction;
import net.minecraft.core.registries.BuiltInRegistries;
import net.minecraft.nbt.CompoundTag;
import net.minecraft.resources.ResourceLocation;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.level.ChunkPos;
import net.minecraft.world.level.block.entity.BlockEntity;
import net.minecraft.world.level.block.state.BlockState;

import java.lang.reflect.Field;
import java.util.ArrayList;
import java.util.Collections;
import java.util.IdentityHashMap;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Objects;
import java.util.Set;

/**
 * SOURCE PROPOSAL ONLY. This is a narrow lifecycle component, not a console
 * controller and not admission authority. The owning future engineering phase
 * must hold the shared exclusive lease, exact current pack/class/world/proof
 * admission, bounded FULL/ticking tickets and the closed-idle BridgePhaseGate.
 * Its guard runs before every observation and every one-time native initializer.
 * This class owns no tickets, futures, wake timer, input, glue or world rollback.
 */
public final class NativeRadioLifecycle {
    @FunctionalInterface public interface Guard { void check() throws Exception; }
    private record Spec(BlockPos position, boolean receiver, Direction facing, String first, String last) {}
    private record Retained(Spec spec, RedstoneLinkBlockEntity entity, LinkBehaviour link,
                            BlockState state, CompoundTag nbt, Object networkKey) {}
    private record Current(List<RadioLifecycleFacts.Actor> facts, Set<?> members,
                           int foreignMembers, boolean prepared) {}

    private static final Map<BlockPos, Boolean> ROLES = Map.of(
        new BlockPos(1183,72,-1178),false, new BlockPos(1183,72,-1110),false,
        new BlockPos(1203,71,-1172),true, new BlockPos(1203,71,-1116),true);
    private final ServerLevel level;
    private final Guard guard;
    private final List<Retained> retained = new ArrayList<>();
    private final Set<LinkBehaviour> owned = Collections.newSetFromMap(new IdentityHashMap<>());
    private final List<BlockPos> attempted = new ArrayList<>();
    private boolean oneRepairInvoked;
    private long lastObservedGameTime = Long.MIN_VALUE;
    private int stableTicks;

    public NativeRadioLifecycle(ServerLevel level, JsonArray radios, Guard guard) throws Exception {
        this.level=Objects.requireNonNull(level); this.guard=Objects.requireNonNull(guard);
        check();
        if (radios.size()!=4) throw new IllegalStateException("Exact two existing bridge transmitters and receivers required");
        Set<BlockPos> positions = new java.util.HashSet<>();
        for (JsonElement element : radios) {
            JsonObject row=element.getAsJsonObject(); JsonArray a=row.getAsJsonArray("position");
            if(a==null || a.size()!=3) throw new IllegalStateException("Exact native radio position required");
            BlockPos pos=new BlockPos(a.get(0).getAsInt(),a.get(1).getAsInt(),a.get(2).getAsInt());
            Boolean receiver=ROLES.get(pos);
            if(receiver==null || !positions.add(pos)) throw new IllegalStateException("Foreign/duplicate bridge radio");
            Spec spec=new Spec(pos,receiver,receiver?Direction.UP:Direction.EAST,
                row.get("first").getAsString(),row.get("last").getAsString());
            if(!simulationReady(pos)) throw new IllegalStateException("Read only already FULL/ticking radio chunks; no loading in lifecycle component");
            BlockEntity raw=level.getBlockEntity(pos);
            if(!(raw instanceof RedstoneLinkBlockEntity entity)) throw new IllegalStateException("Existing native Create link required");
            LinkBehaviour link=entity.getBehaviour(LinkBehaviour.TYPE);
            if(link==null || fieldLink(entity)!=link || link.blockEntity!=entity) throw new IllegalStateException("Registered native behaviour identity differs");
            retained.add(new Retained(spec,entity,link,entity.getBlockState(),
                entity.saveWithFullMetadata(level.registryAccess()).copy(),link.getNetworkKey()));
            if(!owned.add(link)) throw new IllegalStateException("One native behaviour claimed at multiple radios");
        }
        if(!positions.equals(ROLES.keySet())) throw new IllegalStateException("Complete retained four-radio custody required");
        Current now=current();
        if(!RadioLifecycleFacts.admissible(now.facts,now.foreignMembers,now.prepared)) throw new IllegalStateException("Native radio lifecycle admission refused");
    }

    private static LinkBehaviour fieldLink(RedstoneLinkBlockEntity entity) throws Exception {
        Field field=RedstoneLinkBlockEntity.class.getDeclaredField("link"); field.setAccessible(true);
        return (LinkBehaviour)field.get(entity);
    }

    private void check() throws Exception {
        guard.check();
        if(level!=level.getServer().overworld() || !level.getServer().isSameThread() ||
           !level.getServer().getPlayerList().getPlayers().isEmpty()) throw new IllegalStateException("Owned empty server tick required");
    }

    private boolean frequency(LinkBehaviour link, Spec spec) {
        CompoundTag tag=new CompoundTag(); link.write(tag,level.registryAccess(),false); // Read-only serialization.
        ItemStack first=ItemStack.parseOptional(level.registryAccess(),tag.getCompound("FrequencyFirst"));
        ItemStack last=ItemStack.parseOptional(level.registryAccess(),tag.getCompound("FrequencyLast"));
        ResourceLocation a=ResourceLocation.parse(spec.first),b=ResourceLocation.parse(spec.last);
        if(!BuiltInRegistries.ITEM.containsKey(a)||!BuiltInRegistries.ITEM.containsKey(b)) return false;
        return first.getCount()==1 && last.getCount()==1 &&
            ItemStack.isSameItemSameComponents(first,new ItemStack(BuiltInRegistries.ITEM.get(a))) &&
            ItemStack.isSameItemSameComponents(last,new ItemStack(BuiltInRegistries.ITEM.get(b)));
    }

    private boolean simulationReady(BlockPos p) {
        return level.getChunkSource().getChunkNow(p.getX()>>4,p.getZ()>>4)!=null &&
            level.getChunkSource().isPositionTicking(ChunkPos.asLong(p)) &&
            level.isPositionEntityTicking(p) && level.areEntitiesLoaded(ChunkPos.asLong(p));
    }

    private Current current() throws Exception {
        check();
        var handler=Create.REDSTONE_LINK_NETWORK_HANDLER;
        Map<?,?> networks=handler.networksIn(level);
        // An unprepared world returns a new throwaway map on each call. Refuse
        // it rather than creating/replacing a world network as a side effect.
        boolean prepared=networks==handler.networksIn(level);
        Object key=retained.getFirst().networkKey;
        Object value=networks.get(key);
        if(!(value instanceof Set<?> members)) throw new IllegalStateException("Existing transmitter network required; no synthetic empty network");
        int foreign=0;
        for(Object member:members) if(!owned.contains(member)) foreign++;
        List<RadioLifecycleFacts.Actor> facts=new ArrayList<>();
        for(Retained r:retained) {
            BlockPos p=r.spec.position;
            boolean ticking=simulationReady(p);
            if(!ticking) throw new IllegalStateException("Radio FULL/ticking readiness lost; no implicit getBlockState load");
            BlockState state=level.getBlockState(p);
            boolean same=level.getBlockEntity(p)==r.entity && r.entity.getBehaviour(LinkBehaviour.TYPE)==r.link &&
                fieldLink(r.entity)==r.link && r.link.blockEntity==r.entity;
            if(!state.equals(r.state) || !state.hasProperty(RedstoneLinkBlock.RECEIVER) ||
                state.getValue(RedstoneLinkBlock.RECEIVER)!=r.spec.receiver ||
                state.getValue(RedstoneLinkBlock.FACING)!=r.spec.facing ||
                !r.nbt.equals(r.entity.saveWithFullMetadata(level.registryAccess())) ||
                !key.equals(r.link.getNetworkKey()) || !r.networkKey.equals(r.link.getNetworkKey()))
                throw new IllegalStateException("Retained native radio state/NBT/frequency key changed");
            facts.add(new RadioLifecycleFacts.Actor(r.spec.receiver,r.link.isAlive(),same,ticking,
                frequency(r.link,r.spec) && r.link.isListening()==r.spec.receiver,
                members.contains(r.link),state.getValue(RedstoneLinkBlock.POWERED),
                r.link.getTransmittedStrength(),r.entity.getReceivedSignal()));
        }
        for(Retained tx:retained)if(!tx.spec.receiver)for(Retained rx:retained)if(rx.spec.receiver)
            if(!RedstoneLinkNetworkHandler.withinRange(tx.link,rx.link))
                throw new IllegalStateException("Actual native link-range configuration cannot reach both retained receivers");
        return new Current(List.copyOf(facts),members,foreign,prepared);
    }

    /** ONLY a separately admitted recovery action may call this once. */
    public void reattachMissingReceiversOnce() throws Exception {
        if(oneRepairInvoked) throw new IllegalStateException("No repeated receiver initializer in one lease");
        Current now=current();
        if(!RadioLifecycleFacts.admissible(now.facts,now.foreignMembers,now.prepared)) throw new IllegalStateException("Actual receiver recovery facts changed");
        oneRepairInvoked=true;
        for(Retained r:retained) {
            now=current();
            if(!RadioLifecycleFacts.admissible(now.facts,now.foreignMembers,now.prepared)) throw new IllegalStateException("Radio changed before native initializer");
            if(r.spec.receiver && !now.members.contains(r.link)) {
                check(); attempted.add(r.spec.position); // Intent recorded before the real API call.
                r.link.initialize(); // Pinned native addToNetwork + normal zero-power callback only.
            }
        }
        current(); // Complete native blockstate/NBT/identity readback, no caller-supplied signal.
    }

    /** Caller ticks this under the same bounded lease; never wakes an idle world. */
    public boolean observeIdleFortyTicks() throws Exception {
        Current now=current();
        if(!RadioLifecycleFacts.admissible(now.facts,now.foreignMembers,now.prepared)) throw new IllegalStateException("Radio custody/power/lifecycle changed");
        long time=level.getGameTime();
        if(time!=lastObservedGameTime) {
            stableTicks=RadioLifecycleFacts.ready(now.facts,now.foreignMembers,now.prepared)?
                (time==lastObservedGameTime+1?stableTicks+1:1):0;
            lastObservedGameTime=time;
        }
        return stableTicks>=40;
    }

    /** A later, separate commissioned input must still see all idle members. */
    public void requireIdleMembers() throws Exception {
        Current now=current();
        if(!RadioLifecycleFacts.ready(now.facts,now.foreignMembers,now.prepared))
            throw new IllegalStateException("Retained native radio members are not idle/ready; no input or automatic repair");
    }

    public List<String> initializerAttempts() {
        return attempted.stream().map(BlockPos::toShortString).toList();
    }

    public Map<String,Object> facts() throws Exception {
        Current now=current(); List<Object> rows=new ArrayList<>();
        for(int i=0;i<retained.size();i++) rows.add(Map.of("position",retained.get(i).spec.position.toShortString(),
            "receiver",now.facts.get(i).receiver(),"network_member",now.facts.get(i).networkMember(),
            "same_registered_native_behaviour",now.facts.get(i).sameRegisteredBehaviour(),
            "alive",now.facts.get(i).alive(),"transmitted",now.facts.get(i).transmitted(),"received",now.facts.get(i).received()));
        Map<String,Object> report=new LinkedHashMap<>();
        report.put("retained_native_radios",rows);report.put("foreign_network_members",now.foreignMembers);
        report.put("stable_idle_ticks",stableTicks);report.put("normal_receiver_initializer_attempts",attempted.stream().map(BlockPos::toShortString).toList());
        report.put("frequency_program_glue_inventory_kinetic_NBT_or_input_writes",0);
        report.put("native_button_cycles_or_restart_qualified",false);
        return report;
    }
}
