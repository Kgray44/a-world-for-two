package worldfortwo.qa;

/** Pure readiness gate. Frames come from the existing native RenderFrameEvent.Post.
 * Time/poll count can bound a request but cannot make an observation ready.
 */
public final class MapCaptureGate {
    public record Target(String dimension, double x, double z, double zoom) {
        public Target {
            if (dimension == null || !dimension.matches("[a-z0-9_.-]+:[a-z0-9_./-]+")
                    || !Double.isFinite(x) || !Double.isFinite(z) || !Double.isFinite(zoom)
                    || Math.abs(x)>29_999_000 || Math.abs(z)>29_999_000 || zoom<.0625 || zoom>16)
                throw new IllegalArgumentException("A finite bounded native map target is required");
        }
    }
    public record Observation(long frame, String dimension, boolean dimensionReady,
                              double x, double z, double zoom, double targetZoom) {}
    public record Evidence(Observation first, Observation second) {}
    private final Target target;
    private Observation previous;
    private String lastReason="No rendered map observation yet";

    public MapCaptureGate(Target target) { this.target=target; }
    public Target target() { return target; }
    public String lastReason() { return lastReason; }

    public Evidence consider(Observation current) {
        if (!ready(current)) { previous=null; return null; }
        if (previous!=null && current.frame<=previous.frame) {
            lastReason="A second distinct rendered frame is required";return null;
        }
        Observation first=previous;previous=current;
        if (first==null) { lastReason="One ready frame observed; a second agreeing frame is required";return null; }
        if (Math.abs(first.x-current.x)>.25 || Math.abs(first.z-current.z)>.25
                || !near(first.zoom,current.zoom) || !near(first.targetZoom,current.targetZoom)) {
            lastReason="Rendered center or zoom observations do not agree";return null;
        }
        lastReason="Two distinct rendered frames agree on the actual requested native view";
        return new Evidence(first,current);
    }

    private boolean ready(Observation value) {
        if (value==null || value.frame<=0 || !value.dimensionReady || !target.dimension.equals(value.dimension)) {
            lastReason="The actual requested map dimension is not ready";return false;
        }
        if (!Double.isFinite(value.x) || !Double.isFinite(value.z) || !Double.isFinite(value.zoom)
                || !Double.isFinite(value.targetZoom)) { lastReason="Non-finite native view state";return false; }
        if (Math.abs(target.x-value.x)>.5 || Math.abs(target.z-value.z)>.5) {
            lastReason="The actual map center has not reached the requested center";return false;
        }
        if (!near(target.zoom,value.zoom) || !near(target.zoom,value.targetZoom)) {
            lastReason="Actual native zoom has not converged to the requested target";return false;
        }
        return true;
    }
    private static boolean near(double left,double right) { return left>0 && right>0 && Math.abs(left-right)<=Math.max(left,right)*.001; }
}
