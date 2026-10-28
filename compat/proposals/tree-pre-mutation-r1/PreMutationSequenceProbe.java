package worldfortwo.bridge;

import java.util.LinkedHashMap;
import java.util.Map;

/** Pure temporal fixture, not a fake Minecraft Level or native growth claim. */
public final class PreMutationSequenceProbe {
    private static void require(boolean value){if(!value)throw new AssertionError();}
    private static Map<String,String> field(){Map<String,String> m=new LinkedHashMap<>();m.put("early-readonly-water","water[level=0]");m.put("root","tall_grass[half=lower]");m.put("late-perimeter","air");return m;}
    public static void main(String[] args){
        Map<String,String> expected=field(),actual=new LinkedHashMap<>(expected);
        require(expected.get("early-readonly-water").equals(actual.get("early-readonly-water")));
        // Ambient change between old batched VERIFY reads. Last old row still
        // matches, but the immediate WHOLE field check must block the setter.
        actual.put("early-readonly-water","ice");
        require(expected.get("late-perimeter").equals(actual.get("late-perimeter")));
        int[] setterCalls={0},refusals={0};
        try{PreMutationFieldCheck.requireUnchanged(expected,actual::get,d->{refusals[0]++;require(d.position().equals("early-readonly-water"));});setterCalls[0]++;throw new AssertionError();}
        catch(PreMutationFieldCheck.DriftDetected expectedFailure){}
        require(setterCalls[0]==0&&refusals[0]==1);require(actual.get("early-readonly-water").equals("ice"));
        require(actual.get("root").equals("tall_grass[half=lower]"));
        actual=new LinkedHashMap<>(expected);
        require(PreMutationFieldCheck.requireUnchanged(expected,actual::get,d->{throw new AssertionError();})==3);
        actual.put("late-perimeter",null);
        try{PreMutationFieldCheck.requireUnchanged(expected,actual::get,d->require(d.actual()==null));throw new AssertionError();}
        catch(PreMutationFieldCheck.DriftDetected expectedFailure){}
        actual=new LinkedHashMap<>(expected);actual.put("root","tall_grass[half=upper]");
        try{PreMutationFieldCheck.requireUnchanged(expected,actual::get,d->require(d.expected().equals("tall_grass[half=lower]")));throw new AssertionError();}
        catch(PreMutationFieldCheck.DriftDetected expectedFailure){}
        try{PreMutationFieldCheck.requireUnchanged(Map.of(),actual::get,d->{});throw new AssertionError();}
        catch(IllegalArgumentException expectedFailure){}
        System.out.println("Whole-field stale-early-row, property drift and unknown-field refusals passed before any synthetic setter; no native calls or restoration");
    }
}
