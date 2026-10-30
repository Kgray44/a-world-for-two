import com.google.gson.Gson;
import io.github.draysus.chattingvillagers.DialogueManager;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.HashSet;

/** Exact author JAR schema check. Does not launch Minecraft or prove gameplay. */
public final class UpstreamDialogueProbe {
    public static void main(String[] args) throws Exception {
        int count = 0;
        var ids = new HashSet<String>();
        try (var files = Files.list(Path.of(args[0]))) {
            for (Path file : files.filter(p -> p.getFileName().toString().startsWith("awft_")).sorted().toList()) {
                var rows = new Gson().fromJson(Files.readString(file), DialogueManager.SoloLine[].class);
                for (var row : rows) {
                    if (row.id == null || !ids.add(row.id) || !"solo".equals(row.type)
                            || row.text == null || row.text.isBlank() || row.text.length() > 240
                            || row.conditions == null || row.conditions.state.size() != 1
                            || !row.conditions.state.getFirst().startsWith("awft_district_")) {
                        throw new AssertionError("Invalid native dialogue row in " + file);
                    }
                    count++;
                }
            }
        }
        if (count == 0) throw new AssertionError("No dialogue files inspected");
        System.out.println("Exact Chatting Villagers 1.1.0 native JSON schema accepted " + count + " original lines; no Minecraft runtime started.");
    }
}
