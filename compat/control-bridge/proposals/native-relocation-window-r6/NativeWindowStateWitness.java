package worldfortwo.bridge;

import com.google.gson.*;
import java.io.InputStream;
import java.lang.reflect.Proxy;
import java.security.MessageDigest;
import java.util.*;
import net.minecraft.core.BlockPos;
import net.minecraft.core.Direction;
import net.minecraft.world.level.LevelAccessor;
import net.minecraft.world.level.block.Blocks;
import net.minecraft.world.level.block.state.BlockState;
import net.minecraft.world.level.block.state.properties.Property;

/** Original integration of the exact native MCW2.4.2 calculation, no setters. */
public final class NativeWindowStateWitness {
    public static final String TYPE="com.mcwwindows.kikoz.objects.ConnectedWindow";
    private static final String MAIN="fd616dfa6982d5ac3b2ce2f9dd25ef4d8d494cac1ed0550180dbfd7e39c12702";
    private static final String DIRECTIONS="978dc0e042fa144de58209c0598e15a502c90b8bdc3bff9a5b50702887dc7e6f";
    private NativeWindowStateWitness(){}
    public static boolean applies(BlockState original){return original.getBlock().getClass().getName().equals(TYPE);}
    private static String hash(Class<?> type)throws Exception{
        try(InputStream in=type.getResourceAsStream("/"+type.getName().replace('.','/')+".class")){
            if(in==null)throw new IllegalStateException("Exact MCW native API resource unavailable");byte[] raw=in.readNBytes(262145);
            if(raw.length==0||raw.length>262144)throw new IllegalStateException("Bounded native API bytes required");
            return HexFormat.of().formatHex(MessageDigest.getInstance("SHA-256").digest(raw));
        }
    }
    private static void sameNonPart(BlockState original,BlockState value){
        if(original.getBlock()!=value.getBlock()||original.hasBlockEntity()||value.hasBlockEntity())throw new IllegalStateException("Only identical NON-BE connected window identity can derive a part");
        boolean part=false;
        for(Property<?> p:original.getProperties()){
            if(p.getName().equals("part")){part=true;continue;}
            if(!original.getValue(p).equals(value.getValue(p)))throw new IllegalStateException("Native window facing/nonpart property differs");
        }
        if(!part)throw new IllegalStateException("Pinned native window part property missing");
    }
    public record Derived(BlockState expected,JsonObject witness){}
    private static LevelAccessor finiteNeighbors(Map<BlockPos,BlockState> cells){
        return (LevelAccessor)Proxy.newProxyInstance(LevelAccessor.class.getClassLoader(),new Class<?>[]{LevelAccessor.class},(proxy,method,args)->{
            if(method.getName().equals("getBlockState")&&args!=null&&args.length==1){
                BlockState value=cells.get((BlockPos)args[0]);
                if(value==null)throw new IllegalStateException("Native window calculation escaped its six actual neighbors; own-result reads forbidden");
                return value;
            }
            if(method.getName().equals("toString")&&method.getParameterCount()==0)return "READ-ONLY six captured native window neighbors";
            throw new IllegalStateException("Native window calculation attempted an unadmitted API; no writes or fallback");
        });
    }
    public static void pin(BlockState original)throws Exception{
        if(!applies(original)||original.hasBlockEntity())throw new IllegalStateException("Exact NON-BE native window class required before intent");
        Class<?> main=original.getBlock().getClass(),directions=Class.forName(TYPE+"$1",false,main.getClassLoader());
        if(!hash(main).equals(MAIN)||!hash(directions).equals(DIRECTIONS)||directions.getClassLoader()!=main.getClassLoader()||directions.getModule()!=main.getModule())
            throw new IllegalStateException("Exact pinned MCW2.4.2 native classes required");
    }
    /** original is captured BEFORE clone. The actual result NEVER supplies
     * expected properties: native updateShape receives original + real neighbors. */
    public static Derived validate(BlockState original,BlockState actual,LevelAccessor level,BlockPos destination)throws Exception{
        pin(original);sameNonPart(original,actual);
        EnumMap<Direction,BlockState> neighbors=new EnumMap<>(Direction.class);
        for(Direction direction:Direction.values())neighbors.put(direction,level.getBlockState(destination.relative(direction)));
        // ConnectedWindow.updateShape dispatches its native WindowState. The
        // pinned implementation reads only these neighbors and original facing.
        Map<BlockPos,BlockState> finite=new HashMap<>();for(var entry:neighbors.entrySet())finite.put(destination.relative(entry.getKey()).immutable(),entry.getValue());
        BlockState expected=original.updateShape(Direction.UP,neighbors.get(Direction.UP),finiteNeighbors(Map.copyOf(finite)),destination,destination.above());
        sameNonPart(original,expected);
        for(Direction direction:Direction.values())if(!neighbors.get(direction).equals(level.getBlockState(destination.relative(direction))))
            throw new IllegalStateException("Actual native neighbor custody changed during derivation");
        if(!actual.equals(expected))throw new IllegalStateException("Actual window part does not equal independently native-derived full state");
        if(!expected.canSurvive(level,destination)||!actual.canSurvive(level,destination))throw new IllegalStateException("Native window survival failed; never relaxed");
        JsonObject proof=new JsonObject();proof.addProperty("native_class",TYPE);proof.addProperty("native_class_sha256",MAIN);
        proof.addProperty("original_captured_state",original.toString());proof.addProperty("native_expected_full_state",expected.toString());proof.addProperty("actual_full_state",actual.toString());
        proof.addProperty("expected_from_actual_result",false);proof.addProperty("state_or_inventory_writes",0);
        proof.addProperty("calculation_read_scope","six captured actual neighbor states only; own result/API writes refused");
        JsonObject adjacent=new JsonObject();for(var e:neighbors.entrySet())adjacent.addProperty(e.getKey().getName(),e.getValue().toString());proof.add("actual_neighbors_before_and_after_unchanged",adjacent);
        return new Derived(expected,proof);
    }
    @SuppressWarnings({"unchecked","rawtypes"})
    private static BlockState changed(BlockState state,String name){
        Property property=state.getBlock().getStateDefinition().getProperty(name);
        if(property==null)throw new IllegalStateException("Exact native counterfactual property missing");
        for(Object value:property.getPossibleValues())if(!value.equals(state.getValue(property)))return state.setValue(property,(Comparable)value);
        throw new IllegalStateException("Distinct native counterfactual property value required");
    }
    @FunctionalInterface private interface Check{void run()throws Exception;}
    private static JsonObject refused(String name,String exactReason,Check check)throws Exception{
        try{check.run();}catch(IllegalStateException expected){
            if(!String.valueOf(expected.getMessage()).contains(exactReason))throw new IllegalStateException("Counterfactual failed for an unrelated reason: "+name,expected);
            JsonObject row=new JsonObject();row.addProperty("case",name);row.addProperty("rejected",true);row.addProperty("reason",expected.getMessage());return row;
        }
        throw new IllegalStateException("Native counterfactual unexpectedly admitted: "+name);
    }
    /** Runs on the already-registered source window before intent. Arguments are
     * immutable BlockStates; the actual world and all inventories stay untouched. */
    public static JsonObject counterfactuals(BlockState captured,BlockState actualSource,LevelAccessor level,BlockPos source)throws Exception{
        Derived positive=validate(captured,actualSource,level,source);BlockState correct=positive.expected();JsonArray negatives=new JsonArray();
        negatives.add(refused("altered_actual_part","independently native-derived full state",()->validate(captured,changed(correct,"part"),level,source)));
        negatives.add(refused("wrong_source_class","Exact NON-BE native window class",()->validate(Blocks.GLASS.defaultBlockState(),Blocks.GLASS.defaultBlockState(),level,source)));
        negatives.add(refused("replaced_actual_block","identical NON-BE connected window identity",()->validate(captured,Blocks.GLASS.defaultBlockState(),level,source)));
        negatives.add(refused("wrong_actual_facing","facing/nonpart property differs",()->validate(captured,changed(correct,"facing"),level,source)));
        JsonObject result=new JsonObject();result.add("actual_source_positive",positive.witness());result.add("negative_cases",negatives);
        result.addProperty("negative_cases_passed",4);result.addProperty("source","real registered source window and same-tick actual neighbors");result.addProperty("state_or_inventory_writes",0);
        return result;
    }
}
