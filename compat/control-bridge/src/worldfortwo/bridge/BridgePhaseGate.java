package worldfortwo.bridge;

/** Native state, rather than interpolated visual angle alone, admits the next input. */
public final class BridgePhaseGate {
    private BridgePhaseGate(){}
    public static boolean simulationReady(boolean blockTicking,boolean entityTicking,boolean entitiesLoaded,boolean needsSpeedUpdate){
        return blockTicking && entityTicking && entitiesLoaded && !needsSpeedUpdate;
    }
    public static boolean attachmentReady(boolean running,boolean attached,boolean alive,boolean entityTicking,
                                          int ticks,int blocks,double minY,double maxY){
        if(!running)return !attached;
        return attached && alive && entityTicking && ticks>0 && blocks>=100 &&
            Double.isFinite(minY) && Double.isFinite(maxY) && minY<=maxY;
    }
    public static boolean ready(double angle,double target,boolean open,boolean running,double speed,
                                double inputSpeed,boolean sequencerOverstressed,boolean bearingOverstressed,
                                boolean awaiting,boolean idle,boolean powered,int blocks){
        // A stopped output is expected at AWAIT and closed idle. It does not
        // prove the sequencer has power to consume the next input immediately.
        if(!Double.isFinite(inputSpeed) || inputSpeed==0 || sequencerOverstressed || bearingOverstressed)return false;
        if(!Double.isFinite(angle) || !Double.isFinite(speed) || Math.abs(speed)>.001 || powered)return false;
        angle%=360;if(angle>180)angle-=360;if(angle< -180)angle+=360;
        if(open)return Double.isFinite(target) && Math.abs(angle-target)<=.75 && running && awaiting && !idle && blocks>=100;
        return Math.abs(angle)<=.75 && !running && idle && !awaiting;
    }
}
