package worldfortwo.bridge;

import net.minecraft.core.BlockPos;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.tags.BlockTags;
import net.minecraft.world.level.Level;
import net.minecraft.world.level.block.LeavesBlock;
import net.minecraft.world.level.block.SaplingBlock;
import net.minecraft.world.level.block.state.BlockState;
import net.minecraft.world.level.block.state.properties.Property;
import net.minecraft.world.phys.AABB;
import java.util.*;

/** Original synchronous guard for native growth, never a fake/virtual world.
 * An inactive scope has no effect. Parent must wire the isolated Level mixin.
 */
public final class TreeGrowthScope implements AutoCloseable {
    public static final class Probe extends RuntimeException {private Probe(){super("native growth hook witness",null,false,false);}}
    @FunctionalInterface public interface FailedAttemptAction {void run() throws Throwable;}
    public record FailedRecovery(Throwable captureFailure,Throwable restoreFailure) {public boolean exactRestored(){return restoreFailure==null;}}
    /** Failure evidence is optional for recovery: even a broken snapshot must not skip restoration. */
    public static FailedRecovery captureThenRestore(FailedAttemptAction capture,FailedAttemptAction restore){
        Throwable captureFailure=null,restoreFailure=null;
        try{capture.run();}catch(Throwable failure){captureFailure=failure;}
        try{restore.run();}catch(Throwable failure){restoreFailure=failure;}
        return new FailedRecovery(captureFailure,restoreFailure);
    }
    private static final ThreadLocal<TreeGrowthScope> ACTIVE=new ThreadLocal<>();
    private static volatile boolean armed;
    private static final Set<String> SOFT=Set.of("minecraft:short_grass","minecraft:tall_grass","minecraft:fern","minecraft:large_fern",
        "minecraft:dandelion","minecraft:poppy","minecraft:cornflower","minecraft:oxeye_daisy","minecraft:allium",
        "minecraft:azure_bluet","minecraft:lily_of_the_valley","minecraft:blue_orchid","minecraft:dead_bush","minecraft:snow",
        "regions_unexplored:grass_sprouts");
    final ServerLevel level;
    final Map<BlockPos,BlockState> before;
    final AABB writeBounds;
    final Set<Long> protectedColumns;
    final int soilY;
    final boolean allowNativeNest;
    final Set<BlockPos> approvedNativeFoliage;
    final Set<BlockState> approvedNaturalTreeOutputs;
    final BlockPos ownedPreplantedRoot;
    final BlockState ownedPreplantedOriginal;
    final Set<BlockState> ownedPreplantedOutputs;
    final LinkedHashSet<BlockPos> attempted=new LinkedHashSet<>();
    final Map<BlockPos,BlockState> lastExpected=new HashMap<>();
    int reads,writes;
    boolean probe,writeProbeObserved,rollback;
    String violation;
    private boolean closed;
    /* Coordinate grids collide heavily in the JDK's linear-probed immutable
       SetN/MapN tables. Keep detached, null-rejecting snapshots, but retain the
       collision handling of HashSet/HashMap rather than using copyOf here. */
    static <E> Set<E> snapshotSet(Set<? extends E> input){
        Set<E> copy=new HashSet<>();
        for(E value:Objects.requireNonNull(input))copy.add(Objects.requireNonNull(value));
        return Collections.unmodifiableSet(copy);
    }
    static <K,V> Map<K,V> snapshotMap(Map<? extends K,? extends V> input){
        Map<K,V> copy=new HashMap<>();
        Objects.requireNonNull(input).forEach((key,value)->copy.put(Objects.requireNonNull(key),Objects.requireNonNull(value)));
        return Collections.unmodifiableMap(copy);
    }
    public TreeGrowthScope(ServerLevel level,Map<BlockPos,BlockState> before,AABB writeBounds,Set<Long> protectedColumns,int soilY,boolean allowNativeNest){
        this(level,before,writeBounds,protectedColumns,soilY,allowNativeNest,Set.of());
    }
    /** Dense-patch-only permission: exact captured native leaves to native leaves.
     * Legacy calls keep the empty permission set and their original refusals. */
    public TreeGrowthScope(ServerLevel level,Map<BlockPos,BlockState> before,AABB writeBounds,Set<Long> protectedColumns,int soilY,boolean allowNativeNest,Set<BlockPos> approvedNativeFoliage){
        this(level,before,writeBounds,protectedColumns,soilY,allowNativeNest,approvedNativeFoliage,Set.of());
    }
    /** Explicit dense-root opt-in only; legacy constructors retain leaf-only behavior. */
    TreeGrowthScope(ServerLevel level,Map<BlockPos,BlockState> before,AABB writeBounds,Set<Long> protectedColumns,int soilY,boolean allowNativeNest,Set<BlockPos> approvedNativeFoliage,Set<BlockState> approvedNaturalTreeOutputs){
        this(level,before,writeBounds,protectedColumns,soilY,allowNativeNest,approvedNativeFoliage,approvedNaturalTreeOutputs,null,null,Set.of());
    }
    /** Only one exact reviewed pre-existing sapling root; every legacy call keeps no permission. */
    TreeGrowthScope(ServerLevel level,Map<BlockPos,BlockState> before,AABB writeBounds,Set<Long> protectedColumns,int soilY,boolean allowNativeNest,Set<BlockPos> approvedNativeFoliage,Set<BlockState> approvedNaturalTreeOutputs,BlockPos ownedRoot,BlockState ownedOriginal,Set<BlockState> ownedOutputs){
        if(ownedRoot==null){
            if(ownedOriginal!=null||!ownedOutputs.isEmpty())throw new IllegalStateException("No output permission without an exact owned preplanted root");
        }else{
            if(ownedOriginal==null||!ownedOriginal.equals(before.get(ownedRoot))||!(ownedOriginal.getBlock()instanceof SaplingBlock)
                ||!ownedOriginal.hasProperty(SaplingBlock.STAGE)||ownedOriginal.hasBlockEntity()||!ownedOriginal.getFluidState().isEmpty()||ownedOriginal.is(BlockTags.LOGS)
                ||!writeBounds.contains(ownedRoot.getX()+.5,ownedRoot.getY()+.5,ownedRoot.getZ()+.5)
                ||protectedColumns.contains(column(ownedRoot.getX(),ownedRoot.getZ()))||ownedOutputs.isEmpty()||ownedOutputs.size()>260)
                throw new IllegalStateException("Exact captured unprotected native sapling root and finite outputs required");
            for(BlockState output:ownedOutputs){
                boolean ownStage=output.equals(ownedOriginal.setValue(SaplingBlock.STAGE,0))||output.equals(ownedOriginal.setValue(SaplingBlock.STAGE,1));
                if(output.hasBlockEntity()||!output.getFluidState().isEmpty()
                    ||!(output.isAir()||ownStage||output.is(BlockTags.LOGS)||output.getBlock()instanceof LeavesBlock&&output.is(BlockTags.LEAVES)))
                    throw new IllegalStateException("No arbitrary block, BE or fluid is an owned-root tree output");
            }
        }
        this.ownedPreplantedRoot=ownedRoot==null?null:ownedRoot.immutable();this.ownedPreplantedOriginal=ownedOriginal;this.ownedPreplantedOutputs=snapshotSet(ownedOutputs);
        if(approvedNativeFoliage.size()>65536)throw new IllegalStateException("Finite exact native foliage overlap required");
        if(approvedNaturalTreeOutputs.size()>256)throw new IllegalStateException("Finite descriptor-qualified tree output set required");
        this.approvedNaturalTreeOutputs=snapshotSet(approvedNaturalTreeOutputs);
        for(BlockState output:this.approvedNaturalTreeOutputs)if(output.hasBlockEntity()||!output.getFluidState().isEmpty()
            ||!(output.is(BlockTags.LOGS)||output.getBlock()instanceof LeavesBlock&&output.is(BlockTags.LEAVES)))
            throw new IllegalStateException("No arbitrary block, fluid or BE is a natural tree output");
        this.approvedNativeFoliage=snapshotSet(approvedNativeFoliage);
        for(BlockPos p:this.approvedNativeFoliage){BlockState state=before.get(p);if(state==null||!(state.getBlock()instanceof LeavesBlock)||!state.is(BlockTags.LEAVES)
            ||state.hasBlockEntity()||!state.getFluidState().isEmpty()||!writeBounds.contains(p.getX()+.5,p.getY()+.5,p.getZ()+.5)
            ||protectedColumns.contains(column(p.getX(),p.getZ())))throw new IllegalStateException("Unreviewed or protected overlap cell");}
        if(ACTIVE.get()!=null||!level.getServer().isSameThread())throw new IllegalStateException("Nested/off-thread native growth scope refused");
        this.level=level;this.before=snapshotMap(before);this.writeBounds=writeBounds;this.protectedColumns=snapshotSet(protectedColumns);this.soilY=soilY;this.allowNativeNest=allowNativeNest;
        synchronized(TreeGrowthScope.class){if(armed)throw new IllegalStateException("Another native growth scope is armed");ACTIVE.set(this);armed=true;}
    }
    public static long column(int x,int z){return ((long)x<<32)|(z&0xffffffffL);}
    private static IllegalStateException denied(TreeGrowthScope scope,String reason){scope.violation=reason;return new IllegalStateException(reason);}
    public static void read(Level level,BlockPos position){
        if(!armed)return;
        TreeGrowthScope scope=ACTIVE.get();if(scope==null||scope.level!=level)return;
        if(!scope.before.containsKey(position))throw denied(scope,"Native tree read escaped its fully known plot: "+position);
        scope.reads++;
    }
    static boolean foliageOverlap(boolean approved,boolean oldLeaves,boolean oldLog,boolean oldBE,boolean oldFluid,
            boolean newLeaves,boolean newLog,boolean newBE,boolean newFluid){
        return approved&&oldLeaves&&!oldLog&&!oldBE&&!oldFluid&&newLeaves&&!newLog&&!newBE&&!newFluid;
    }
    static boolean naturalCanopyOverlap(boolean enabled,boolean approved,boolean oldLeaves,boolean oldPersistent,boolean oldLog,
            boolean oldBE,boolean oldFluid,boolean exactQualifiedOutput,boolean newBE,boolean newFluid){
        return enabled&&approved&&oldLeaves&&!oldPersistent&&!oldLog&&!oldBE&&!oldFluid&&exactQualifiedOutput&&!newBE&&!newFluid;
    }
    static boolean ownedPreplantedPermission(boolean enabled,boolean exactPosition,boolean exactOriginal,boolean originalSapling,
            boolean originalLog,boolean originalBE,boolean originalFluid,boolean qualifiedOutput,boolean desiredBE,boolean desiredFluid){
        return enabled&&exactPosition&&exactOriginal&&originalSapling&&!originalLog&&!originalBE&&!originalFluid&&qualifiedOutput&&!desiredBE&&!desiredFluid;
    }
    /** Neighbor-distance bookkeeping only; never permits another leaf material or property change. */
    static boolean naturalLeafDistanceOnly(boolean explicitNaturalCanopy,BlockState original,BlockState desired){
        if(!explicitNaturalCanopy||original==null||desired==null||original.getBlock()!=desired.getBlock()
            ||!(original.getBlock()instanceof LeavesBlock)||!original.hasProperty(LeavesBlock.DISTANCE)||!desired.hasProperty(LeavesBlock.DISTANCE)
            ||!original.hasProperty(LeavesBlock.PERSISTENT)||!desired.hasProperty(LeavesBlock.PERSISTENT)
            ||original.getValue(LeavesBlock.PERSISTENT)||desired.getValue(LeavesBlock.PERSISTENT)
            ||original.hasBlockEntity()||desired.hasBlockEntity()||!original.getFluidState().isEmpty()||!desired.getFluidState().isEmpty())return false;
        int from=original.getValue(LeavesBlock.DISTANCE),to=desired.getValue(LeavesBlock.DISTANCE);
        return from>=1&&from<=7&&to>=1&&to<=7&&from!=to
            &&original.setValue(LeavesBlock.DISTANCE,to).equals(desired);
    }
    @SuppressWarnings({"rawtypes","unchecked"}) private static String diagnosticState(BlockState state){
        if(state==null)return "UNKNOWN";
        StringJoiner props=new StringJoiner(",");
        state.getProperties().stream().sorted(Comparator.comparing(Property::getName)).forEach(p->props.add(p.getName()+"="+((Property)p).getName((Comparable)state.getValue(p))));
        String value=net.minecraft.core.registries.BuiltInRegistries.BLOCK.getKey(state.getBlock())+(state.getProperties().isEmpty()?"":"["+props+"]");
        return value.length()>512?value.substring(0,512)+"(truncated)":value;
    }
    public static void write(Level level,BlockPos position,BlockState desired){
        if(!armed)return;
        TreeGrowthScope scope=ACTIVE.get();if(scope==null||scope.level!=level)return;
        if(scope.probe){scope.writeProbeObserved=true;throw new Probe();}
        if(scope.violation!=null&&!scope.rollback)throw new IllegalStateException("Native growth already refused: "+scope.violation);
        BlockState original=scope.before.get(position);
        if(original==null||!scope.writeBounds.contains(position.getX()+.5,position.getY()+.5,position.getZ()+.5)
            ||scope.protectedColumns.contains(column(position.getX(),position.getZ())))throw denied(scope,"Native tree write escaped owned envelope/protection: "+position);
        if(scope.rollback){if(!desired.equals(original)||!scope.attempted.contains(position))throw denied(scope,"Rollback may restore only exact owned preimages");return;}
        BlockState current=level.getBlockState(position);
        if(!current.equals(scope.lastExpected.getOrDefault(position,original)))throw denied(scope,"Native growth target changed outside this synchronous transaction: "+position);
        if(current.equals(desired))return; // A no-op is not permission to change protected material.
        String id=net.minecraft.core.registries.BuiltInRegistries.BLOCK.getKey(original.getBlock()).toString();
        boolean nativeFoliageOnly=foliageOverlap(scope.approvedNativeFoliage.contains(position),
            original.getBlock()instanceof LeavesBlock&&original.is(BlockTags.LEAVES),original.is(BlockTags.LOGS),original.hasBlockEntity(),!original.getFluidState().isEmpty(),
            desired.getBlock()instanceof LeavesBlock&&desired.is(BlockTags.LEAVES),desired.is(BlockTags.LOGS),desired.hasBlockEntity(),!desired.getFluidState().isEmpty());
        boolean naturalCanopy=naturalCanopyOverlap(!scope.approvedNaturalTreeOutputs.isEmpty(),scope.approvedNativeFoliage.contains(position),
            original.getBlock()instanceof LeavesBlock&&original.is(BlockTags.LEAVES),
            !original.hasProperty(LeavesBlock.PERSISTENT)||original.getValue(LeavesBlock.PERSISTENT),original.is(BlockTags.LOGS),
            original.hasBlockEntity(),!original.getFluidState().isEmpty(),scope.approvedNaturalTreeOutputs.contains(desired),desired.hasBlockEntity(),!desired.getFluidState().isEmpty());
        boolean ownedRootAllowed=ownedPreplantedPermission(scope.ownedPreplantedRoot!=null,
            position.equals(scope.ownedPreplantedRoot),original.equals(scope.ownedPreplantedOriginal),original.getBlock()instanceof SaplingBlock,
            original.is(BlockTags.LOGS),original.hasBlockEntity(),!original.getFluidState().isEmpty(),scope.ownedPreplantedOutputs.contains(desired),
            desired.hasBlockEntity(),!desired.getFluidState().isEmpty());
        // A new mode never broadens old persistent-leaf permission accidentally.
        boolean leafDistanceOnly=naturalLeafDistanceOnly(!scope.approvedNaturalTreeOutputs.isEmpty(),original,desired);
        boolean canopyAllowed=scope.approvedNaturalTreeOutputs.isEmpty()?nativeFoliageOnly:(naturalCanopy||leafDistanceOnly);
        if(original.hasBlockEntity()||(level.getBlockEntity(position)!=null&&!scope.attempted.contains(position))||!original.getFluidState().isEmpty()
            ||original.getBlock() instanceof LeavesBlock&&!canopyAllowed||original.is(BlockTags.LOGS)
            ||!(ownedRootAllowed||canopyAllowed||original.isAir()||SOFT.contains(id)||(position.getY()<=scope.soilY&&original.is(BlockTags.DIRT))))
            throw denied(scope,"Preserve existing tree, fluid, structure or furnishing: "+position+" original="+diagnosticState(original)+" desired="+diagnosticState(desired));
        try{TreeBeeAudit.desired(original,desired,scope.allowNativeNest);}
        catch(Throwable beeRefusal){
            IllegalStateException refused=denied(scope,"Native bee-nest admission refused");
            refused.addSuppressed(beeRefusal);throw refused;
        }
        scope.attempted.add(position.immutable());scope.lastExpected.put(position.immutable(),desired);scope.writes++;
        if(scope.attempted.size()>65536||scope.writes>262144)throw denied(scope,"Finite native tree write budget exceeded");
    }
    public void hookWitness(BlockPos root){
        int count=reads;level.getBlockState(root);if(reads==count)throw new IllegalStateException("Required native Level read hook is not installed");
        probe=true;try{level.setBlock(root,level.getBlockState(root),2|16);throw new IllegalStateException("Required native Level write hook is not installed");}
        catch(Probe expected){if(!writeProbeObserved)throw new IllegalStateException("Native write witness missing");}
        finally{probe=false;}
    }
    public int restoreFailedAttempt(){
        rollback=true;int restored=0;List<BlockPos> reverse=new ArrayList<>(attempted);Collections.reverse(reverse);
        for(BlockPos pos:reverse){BlockState original=before.get(pos);if(!level.getBlockState(pos).equals(original)){if(!level.setBlock(pos,original,2|16))throw new IllegalStateException("Exact failed-growth restoration refused at "+pos);restored++;}}
        for(BlockPos pos:attempted)if(!level.getBlockState(pos).equals(before.get(pos)))throw new IllegalStateException("Failed native growth left an unreviewed residual state");
        return restored;
    }
    public void close(){if(closed)return;if(ACTIVE.get()!=this)throw new IllegalStateException("Native growth scope ownership changed");synchronized(TreeGrowthScope.class){armed=false;ACTIVE.remove();closed=true;}}
}
