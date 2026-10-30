import com.electronwill.nightconfig.core.Config;
import com.electronwill.nightconfig.toml.TomlParser;
import java.nio.file.Files;
import java.nio.file.Path;
import tn.naizo.smartvillagers.config.SmartVillagersConfig;

/** Read only the exact author's configuration parser; no server/provider boot. */
public final class UpstreamSmartConfigProbe {
    public static void main(String[] args) throws Exception {
        Config input = new TomlParser().parse(Files.readString(Path.of(args[0])));
        var read = SmartVillagersConfig.class.getDeclaredMethod("readSnapshot", Config.class);
        read.setAccessible(true);
        var config = (SmartVillagersConfig.Snapshot) read.invoke(null, input);
        if (config.voiceEnabled() || config.requestsEnabled() || !config.requirePlayerOptIn()
                || !config.requirePrefix() || config.maxConcurrent() != 2
                || config.globalRequestsPerMinute() != 12 || !config.model().isBlank()
                || config.maxReplyChars() != 180 || !config.speechBubbles()
                || !config.provider().name().equals("CUSTOM")) {
            throw new AssertionError("The upstream parser changed a required default");
        }
        System.out.println("Exact Smart Villagers 2.0.0 native TOML parser accepted conservative configuration; no Minecraft/provider runtime started.");
    }
}
