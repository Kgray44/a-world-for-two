package worldfortwo.bridge;

import java.util.List;

/** Original admission facts. No native setter, signal, frequency or motion API. */
public final class RadioLifecycleFacts {
    private RadioLifecycleFacts() {}
    public record Actor(boolean receiver, boolean alive, boolean sameRegisteredBehaviour,
                        boolean simulationReady, boolean frequencyMatches,
                        boolean networkMember, boolean powered, int transmitted, int received) {}

    public static boolean admissible(List<Actor> actors, int foreignMembers, boolean preparedWorld) {
        if (!preparedWorld || foreignMembers != 0 || actors.size() != 4) return false;
        int receivers = 0;
        for (Actor a : actors) {
            if (!a.alive || !a.sameRegisteredBehaviour || !a.simulationReady || !a.frequencyMatches ||
                a.powered || a.transmitted != 0 || a.received != 0) return false;
            if (a.receiver) receivers++;
            else if (!a.networkMember) return false; // Never manufacture a missing transmitter.
        }
        return receivers == 2;
    }

    public static boolean ready(List<Actor> actors, int foreignMembers, boolean preparedWorld) {
        return admissible(actors, foreignMembers, preparedWorld) && actors.stream().allMatch(Actor::networkMember);
    }
}
