package worldfortwo.tavern;

import java.util.*;

/** Deterministic, bounded decisions; independent of Minecraft for meaningful tests. */
public final class ActivityPolicy {
    public record Slot(String id, String group, List<String> activities) {}
    public record Choice(Slot slot, String activity, int ticks) {}
    private ActivityPolicy() {}

    public static Optional<Choice> choose(Random random, List<Slot> slots,
            Set<String> occupied, List<String> history, Map<String,Integer> preferences,
            boolean musicPlaying, boolean musician) {
        List<Choice> choices=new ArrayList<>();
        List<Integer> weights=new ArrayList<>();
        int total=0;
        for (Slot slot: slots) {
            if (occupied.contains(slot.id()) || history.stream().limit(3).anyMatch(slot.id()::equals)) continue;
            for (String act:slot.activities()) {
                if (act.equals("music") || (act.equals("watch") && !musicPlaying)) continue;
                int weight=Math.max(1, Math.min(12, preferences.getOrDefault(act,2)));
                if (musician && act.equals("social")) weight+=2;
                int low=act.equals("walk")?10:(act.equals("bar")||act.equals("drink"))?20:
                    (act.equals("social")||act.equals("group"))?25:30;
                int high=act.equals("walk")?20:(act.equals("bar")||act.equals("drink"))?45:60;
                int ticks=(low+random.nextInt(high-low+1))*20;
                choices.add(new Choice(slot,act,ticks));weights.add(weight);total+=weight;
            }
        }
        if (total==0) return Optional.empty();
        int draw=random.nextInt(total);
        for (int i=0;i<choices.size();i++) {
            draw-=weights.get(i);if(draw<0)return Optional.of(choices.get(i));
        }
        throw new IllegalStateException("Unreachable weighted decision");
    }

    public static UUID identity(String id) {
        return UUID.nameUUIDFromBytes(("awft:drowned-rose:"+id).getBytes(java.nio.charset.StandardCharsets.UTF_8));
    }

    /** Preserve short unfinished activities; cap legacy multi-minute dwell and stagger expiry. */
    public static long resumeDeadline(long saved, long now, UUID resident) {
        return saved>now?Math.min(saved,now+200+Math.floorMod(resident.hashCode(),1001)):
            now+20+Math.floorMod(resident.hashCode(),600);
    }

    /** Never fall back to a repeated line when both histories exclude every choice. */
    public static Optional<String> dialogue(Random random,List<String> lines,
            Collection<String> personalRecent,Collection<String> globalRecent){
        List<String> eligible=lines.stream().filter(s->!personalRecent.contains(s)&&!globalRecent.contains(s)).toList();
        return eligible.isEmpty()?Optional.empty():Optional.of(eligible.get(random.nextInt(eligible.size())));
    }

    public static boolean rugTransit(String state,String above) {
        return (state.equals("minecraft:red_carpet")||state.equals("minecraft:brown_carpet"))
            && above.equals("minecraft:air");
    }

    public static boolean insideTavernFootprint(double x,double z) {
        return x>=1293.3&&x<=1310.7&&z>=-1287.7&&z<=-1270.3;
    }
}
