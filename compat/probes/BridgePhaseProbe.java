import worldfortwo.bridge.BridgePhaseGate;

public final class BridgePhaseProbe {
    private static int checks;
    private static void require(String label,boolean value){
        if(!value)throw new AssertionError("Native bridge phase gate regressed: "+label);
        checks++;
    }
    public static void main(String[] args){
        require("moving output",!BridgePhaseGate.ready(-55,-55,true,true,2,2,false,false,false,false,false,523));
        require("await instruction required",!BridgePhaseGate.ready(-55,-55,true,true,0,2,false,false,false,false,false,523));
        require("input already powered",!BridgePhaseGate.ready(-55,-55,true,true,0,2,false,false,true,false,true,523));
        require("opposed sign",!BridgePhaseGate.ready(55,-55,true,true,0,2,false,false,true,false,false,523));
        require("native contraption required",!BridgePhaseGate.ready(-55,-55,true,true,0,2,false,false,true,false,false,0));
        require("negative 55 open",BridgePhaseGate.ready(-55,-55,true,true,0,2,false,false,true,false,false,523));
        require("positive 55 open",BridgePhaseGate.ready(55,55,true,true,0,2,false,false,true,false,false,508));
        require("legacy 90 recovery",BridgePhaseGate.ready(-90,-90,true,true,0,2,false,false,true,false,false,523));
        require("closed must disassemble",!BridgePhaseGate.ready(0,55,false,true,0,2,false,false,false,true,false,523));
        require("closed must idle",!BridgePhaseGate.ready(0,55,false,false,0,2,false,false,false,false,false,0));
        require("invalid bearing output",!BridgePhaseGate.ready(0,55,false,false,Double.NaN,2,false,false,false,true,false,0));
        require("closed idle ready",BridgePhaseGate.ready(0,55,false,false,0,2,false,false,false,true,false,0));
        // A phase can look ready after a power loss. Neither an opening nor
        // closing input may be consumed until real native input power returns.
        for(boolean open:new boolean[]{false,true}){
            for(double power:new double[]{0d,-0d,Double.NaN,Double.POSITIVE_INFINITY,Double.NEGATIVE_INFINITY})
                require("reject input power "+power+" open="+open,!BridgePhaseGate.ready(open?-55:0,-55,open,open,0,power,false,false,open,!open,false,open?523:0));
            require("sequencer overstress open="+open,!BridgePhaseGate.ready(open?-55:0,-55,open,open,0,2,true,false,open,!open,false,open?523:0));
            require("bearing overstress open="+open,!BridgePhaseGate.ready(open?-55:0,-55,open,open,0,2,false,true,open,!open,false,open?523:0));
            require("both overstressed open="+open,!BridgePhaseGate.ready(open?-55:0,-55,open,open,0,2,true,true,open,!open,false,open?523:0));
            require("restored forward power open="+open,BridgePhaseGate.ready(open?-55:0,-55,open,open,0,2,false,false,open,!open,false,open?523:0));
            require("reverse input power open="+open,BridgePhaseGate.ready(open?-55:0,-55,open,open,0,-2,false,false,open,!open,false,open?523:0));
        }
        require("native simulation ready",BridgePhaseGate.simulationReady(true,true,true,false));
        require("FULL without block ticks",!BridgePhaseGate.simulationReady(false,true,true,false));
        require("FULL without entity ticks",!BridgePhaseGate.simulationReady(true,false,true,false));
        require("entity disk load pending",!BridgePhaseGate.simulationReady(true,true,false,false));
        require("kinetic initialization pending",!BridgePhaseGate.simulationReady(true,true,true,true));
        require("real live attachment",BridgePhaseGate.attachmentReady(true,true,true,true,1,523,69,100));
        require("saved running is not attachment",!BridgePhaseGate.attachmentReady(true,false,false,true,0,0,Double.NaN,Double.NaN));
        require("removed entity",!BridgePhaseGate.attachmentReady(true,true,false,true,1,523,69,100));
        require("entity not ticking",!BridgePhaseGate.attachmentReady(true,true,true,false,1,523,69,100));
        require("entity has not ticked",!BridgePhaseGate.attachmentReady(true,true,true,true,0,523,69,100));
        require("native blocks absent",!BridgePhaseGate.attachmentReady(true,true,true,true,1,0,69,100));
        require("invalid actual lower bound",!BridgePhaseGate.attachmentReady(true,true,true,true,1,523,Double.NaN,100));
        require("invalid actual upper bound",!BridgePhaseGate.attachmentReady(true,true,true,true,1,523,69,Double.POSITIVE_INFINITY));
        require("reversed actual bounds",!BridgePhaseGate.attachmentReady(true,true,true,true,1,523,100,69));
        require("closed disassembled",BridgePhaseGate.attachmentReady(false,false,false,false,0,0,Double.NaN,Double.NaN));
        require("closed still attached",!BridgePhaseGate.attachmentReady(false,true,true,true,1,523,69,100));
        System.out.println(checks+" native phase-gate regression checks passed");
    }
}
