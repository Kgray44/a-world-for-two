package worldfortwo.bridge;

import java.lang.reflect.Proxy;
import java.util.*;
import com.mcwwindows.kikoz.objects.ConnectedWindow;
import net.minecraft.SharedConstants;
import net.minecraft.server.Bootstrap;
import net.minecraft.core.BlockPos;
import net.minecraft.world.level.LevelAccessor;
import net.minecraft.world.level.block.Blocks;
import net.minecraft.world.level.block.state.BlockBehaviour;
import net.minecraft.world.level.block.state.BlockState;
import net.minecraft.world.level.block.state.properties.Property;

/** Exact pinned binary on explicit read-only neighbor fixtures, not a Level. */
public final class NativeWindowWitnessProbe {
    private static int assertions;
    @SuppressWarnings({"unchecked","rawtypes"}) private static BlockState with(BlockState s,String key,String value){
        Property p=s.getProperties().stream().filter(v->v.getName().equals(key)).findFirst().orElseThrow();
        return s.setValue(p,(Comparable)p.getValue(value).orElseThrow());
    }
    @FunctionalInterface interface Action {void run()throws Exception;}
    private static void refused(Action action)throws Exception{try{action.run();throw new AssertionError("Unexpected admission");}catch(IllegalStateException expected){assertions++;}}
    public static void main(String[] args)throws Exception{
        SharedConstants.tryDetectVersion();Bootstrap.bootStrap();
        ConnectedWindow block=new ConnectedWindow(BlockBehaviour.Properties.of().noOcclusion());
        BlockPos target=new BlockPos(1,70,3);BlockState original=with(with(block.defaultBlockState(),"facing","east"),"part","bot_r");
        Map<BlockPos,BlockState> states=new HashMap<>();states.put(target.above(),with(original,"part","top_r"));
        int[] selfReads={0};LevelAccessor neighbors=(LevelAccessor)Proxy.newProxyInstance(LevelAccessor.class.getClassLoader(),new Class<?>[]{LevelAccessor.class},(proxy,method,input)->{
            if(method.getName().equals("getBlockState")){BlockPos p=(BlockPos)input[0];if(p.equals(target)){selfReads[0]++;throw new AssertionError("Expected calculation read the actual result cell");}return states.getOrDefault(p,Blocks.AIR.defaultBlockState());}
            if(method.getName().equals("toString"))return "READ-ONLY finite neighbor fixture, no world";
            throw new AssertionError("Pinned calculation attempted non-read-only fixture API: "+method.getName());
        });
        BlockState bottom=with(original,"part","bottom");var first=NativeWindowStateWitness.validate(original,bottom,neighbors,target);
        if(!first.expected().equals(bottom)||first.witness().get("expected_from_actual_result").getAsBoolean())throw new AssertionError("Wrong native expectation");assertions++;
        refused(()->NativeWindowStateWitness.validate(original,with(bottom,"part","top"),neighbors,target));
        refused(()->NativeWindowStateWitness.validate(Blocks.GLASS.defaultBlockState(),Blocks.GLASS.defaultBlockState(),neighbors,target));
        refused(()->NativeWindowStateWitness.validate(original,Blocks.GLASS.defaultBlockState(),neighbors,target));
        refused(()->NativeWindowStateWitness.validate(original,with(bottom,"facing","north"),neighbors,target));
        states.put(target.south(),bottom);var quad=NativeWindowStateWitness.validate(original,original,neighbors,target);
        if(!quad.expected().equals(original))throw new AssertionError("Original real quad context did not restore bot_r");assertions++;
        refused(()->NativeWindowStateWitness.validate(original,bottom,neighbors,target));
        if(selfReads[0]!=0)throw new AssertionError("Actual result contaminated expected state");
        System.out.println("PASS "+assertions+" exact pinned MCW function/counterfactual checks; actual result self-reads=0; no Level/entity/world constructed");
    }
}
