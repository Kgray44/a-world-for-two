package worldfortwo.qa;

/** Headless, event-shaped fixtures only. No Minecraft or GUI initialization. */
public final class MapCaptureGateProbe {
    private static int checks;
    private static void check(boolean value,String name) { checks++;if(!value)throw new AssertionError(name); }
    private static MapCaptureGate.Target target() { return new MapCaptureGate.Target("minecraft:overworld",288,-2272,.5); }
    private static MapCaptureGate.Observation observation(long frame,double x,double z,double zoom) {
        return new MapCaptureGate.Observation(frame,"minecraft:overworld",true,x,z,zoom,.5);
    }
    public static void main(String[] args) {
        var gate=new MapCaptureGate(target());
        check(gate.consider(observation(1,288,-2272,.5))==null,"one frame cannot capture");
        check(gate.consider(observation(1,288,-2272,.5))==null,"duplicate frame cannot capture");
        check(gate.consider(observation(0,288,-2272,.5))==null,"invalid frame resets readiness");
        check(gate.consider(observation(2,288,-2272,.5))==null,"reset requires a first ready frame");
        var proof=gate.consider(observation(3,288,-2272,.5));
        check(proof!=null && proof.first().frame()==2 && proof.second().frame()==3,"two actual distinct agreeing frames accepted");
        gate=new MapCaptureGate(target());
        check(gate.consider(new MapCaptureGate.Observation(1,"minecraft:the_nether",true,288,-2272,.5,.5))==null,"wrong dimension rejected");
        check(gate.consider(new MapCaptureGate.Observation(2,"minecraft:overworld",false,288,-2272,.5,.5))==null,"native dimension not ready rejected");
        check(gate.consider(observation(3,289,-2272,.5))==null,"wrong center rejected");
        check(gate.consider(observation(4,288,-2272,.51))==null,"animated zoom rejected");
        check(gate.consider(new MapCaptureGate.Observation(5,"minecraft:overworld",true,288,-2272,.5,.6))==null,"wrong native target zoom rejected");
        check(gate.consider(observation(6,Double.NaN,-2272,.5))==null,"NaN actual position rejected");
        check(gate.consider(observation(7,288,-2272,Double.POSITIVE_INFINITY))==null,"infinite actual zoom rejected");
        check(gate.consider(observation(8,288.4,-2272,.5))==null,"first edge-tolerance observation pending");
        check(gate.consider(observation(9,287.6,-2272,.5))==null,"individually valid centers must still agree");
        check(gate.consider(observation(10,287.65,-2272,.5))!=null,"new pair after drift can agree");
        gate=new MapCaptureGate(target());
        check(gate.consider(observation(20,288,-2272,.5))==null,"new request requires its own first observation");
        check(gate.consider(observation(19,288,-2272,.5))==null,"older frame cannot be the second");
        check(gate.consider(observation(21,288.1,-2272,.5001))!=null,"bounded native jitter and converged zoom accepted");
        for(double value:new double[]{Double.NaN,Double.POSITIVE_INFINITY,0,32}) {
            boolean rejected=false;
            try { new MapCaptureGate.Target("minecraft:overworld",288,-2272,value); }
            catch(IllegalArgumentException expected) { rejected=true; }
            check(rejected,"invalid target zoom rejected");
        }
        boolean rejected=false;
        try { new MapCaptureGate.Target("minecraft:overworld",30_000_000,-2272,.5); }
        catch(IllegalArgumentException expected) { rejected=true; }
        check(rejected,"world bounds enforced");
        System.out.println("MAP_CAPTURE_GATE_CHECKS="+checks+" PASS; no native GUI executed");
    }
}
