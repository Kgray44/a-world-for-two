package worldfortwo.bridge;

import java.util.List;
import java.util.ArrayList;

/** Synthetic branch probe only, not Minecraft/network or motion evidence. */
public final class RadioLifecycleProbe {
    private static RadioLifecycleFacts.Actor actor(boolean rx, boolean member) {
        return new RadioLifecycleFacts.Actor(rx,true,true,true,true,member,false,0,0);
    }
    private static void require(boolean value) { if(!value) throw new AssertionError(); }
    public static void main(String[] args) {
        List<RadioLifecycleFacts.Actor> missing=List.of(actor(false,true),actor(false,true),actor(true,false),actor(true,false));
        require(RadioLifecycleFacts.admissible(missing,0,true));
        require(!RadioLifecycleFacts.ready(missing,0,true));
        List<RadioLifecycleFacts.Actor> ready=List.of(actor(false,true),actor(false,true),actor(true,true),actor(true,true));
        require(RadioLifecycleFacts.ready(ready,0,true));
        require(!RadioLifecycleFacts.admissible(missing,1,true));
        require(!RadioLifecycleFacts.admissible(missing,0,false));
        List<RadioLifecycleFacts.Actor> bad=new ArrayList<>(missing);
        bad.set(0,actor(false,false));require(!RadioLifecycleFacts.admissible(bad,0,true));
        for(int which=0;which<7;which++) {
            bad=new ArrayList<>(missing);
            bad.set(2,new RadioLifecycleFacts.Actor(true,which!=0,which!=1,which!=2,which!=3,false,
                which==4,which==5?15:0,which==6?15:0));
            require(!RadioLifecycleFacts.admissible(bad,0,true));
        }
        require(!RadioLifecycleFacts.admissible(List.of(actor(false,true),actor(true,false)),0,true));
        require(!RadioLifecycleFacts.admissible(List.of(actor(false,true),actor(false,true),actor(false,true),actor(true,false)),0,true));
        System.out.println("15 synthetic lifecycle readiness/recovery branch assertions passed; no native game calls");
    }
}
