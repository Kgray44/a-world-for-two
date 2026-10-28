import com.google.gson.*;
import java.util.UUID;
import worldfortwo.living.WorldCharacters;

/** Source-level behavior checks for the pure adapter core, without Minecraft. */
public final class WorldCharactersSelfTest {
    private static final UUID BILL = UUID.fromString("310fb254-b839-4fa8-9684-603a4059490d");
    private static void check(boolean value, String message) {
        if (!value) throw new AssertionError(message);
    }
    public static void main(String[] args) {
        JsonObject document = JsonParser.parseString("""
          {"revision":"source-test","settings":{"external_enabled":true,"requests_per_hour":2},
           "districts":[{"id":"tortuga","bounds":{"dimension":"minecraft:overworld",
             "min_x":100,"max_x":120,"min_z":-40,"max_z":-20},
             "entries":[{"id":"harbor","kind":"fact","text":"Tortuga has a harbor.","source":"author map","topics":["harbor"]},
               {"id":"secret","kind":"fact","text":"PRIVATE SECRET","source":"owner","secret":true,"topics":[]},
               {"id":"rumor","kind":"rumor","text":"A kraken collects cutlery.","topics":["kraken"]},
               {"id":"unknown","kind":"fact","text":"UNVERIFIED COORDINATES","topics":[]}],
             "dialogue":{"greetings":["Mind the gull. It owns the till."]}}],
           "characters":[{"id":"bill","entity_uuid":"310fb254-b839-4fa8-9684-603a4059490d",
             "enabled":true,"kind":"villager","district":"tortuga",
             "knowledge":{"inherit_district":true,"allow_rumors":false,"forbidden_topics":["password"],"entries":[]},
             "dialogue":{"max_response_chars":180,"lines":{"jokes":["The sea has declined my invoice."]}},
             "ai":{"enabled":true,"memory_enabled":false,"cooldown_seconds":10,"requests_per_hour":2}}]}
          """).getAsJsonObject();
        WorldCharacters value = new WorldCharacters(document);
        WorldCharacters.current = value;
        JsonObject bill = value.profile(BILL);
        check(value.enabled(bill), "Bound villager should be enabled");
        check(value.profile(UUID.randomUUID()) == null, "No name-based entity fallback");
        check(value.district(UUID.randomUUID(), "minecraft:overworld", 100, -40).equals("tortuga"), "Bounds are inclusive");
        check(value.district(UUID.randomUUID(), "minecraft:overworld", 121, -40).isEmpty(), "Outside district must not inherit lore");
        check(value.district(UUID.randomUUID(), "minecraft:the_nether", 100, -40).isEmpty(), "Dimension isolation");
        check(value.line(bill, "jokes").equals("The sea has declined my invoice."), "Personal authored line wins");
        check(value.line(bill, "greetings").contains("gull"), "District fallback works offline");
        String lore = value.lore(bill, "Tell me about the harbor and kraken");
        check(lore.contains("Tortuga has a harbor"), "Relevant verified fact missing");
        check(!lore.contains("PRIVATE") && !lore.contains("UNVERIFIED") && !lore.contains("cutlery"), "Secret, unverified and disabled-rumor isolation");
        check(value.lore(bill, "what is the password").contains("Decline"), "Forbidden topic refusal");
        check(!value.lore(bill, "turnips").contains("harbor"), "Irrelevant district facts should not be sent");
        check(value.admit(bill, 100000), "First user request should fit budget");
        check(!value.admit(bill, 100001), "Cooldown must charge unsuccessful repeat");
        check(value.admit(bill, 111000), "Next cooled request should fit budget");
        check(!value.admit(bill, 122000), "Hourly request budget must refuse third request");
        check(value.admit(bill, 3700001), "Expired hourly entries should free bounded slots");
        Object memory = new Object(); value.memory(memory, BILL);
        check(!WorldCharacters.memoryEnabled(memory), "Memory off by default");
        JsonObject animal = bill.deepCopy(); animal.addProperty("kind", "animal");
        check(!value.enabled(animal), "Animal authoring cannot silently enable a villager adapter");
        document.getAsJsonArray("characters").add(bill.deepCopy());
        try {new WorldCharacters(document); throw new AssertionError("Duplicate entity binding accepted");}
        catch (IllegalArgumentException expected) {}
        System.out.println("WorldCharacters source checks passed: identity, district, lore, scripted fallback, privacy, request bounds and memory defaults. No Minecraft runtime started.");
    }
}
