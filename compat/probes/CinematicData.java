import com.google.gson.JsonParser;
import dev.tysontheember.lumiera.cinematics.CinematicJsonParser;
import dev.tysontheember.lumiera.cinematics.CinematicsRegistry;
import dev.tysontheember.lumiera.cinematics.event.BuiltinEventParsers;
import net.minecraft.resources.ResourceLocation;
import java.nio.file.Files;
import java.nio.file.Path;

/** Exercises the pinned mod's real parser without starting a Minecraft world. */
public class CinematicData {
    public static void main(String[] args) throws Exception {
        net.minecraft.SharedConstants.tryDetectVersion();
        net.minecraft.server.Bootstrap.bootStrap();
        BuiltinEventParsers.registerAll();
        var parsed = CinematicJsonParser.parseCutscene(ResourceLocation.parse("awft:intro"),
            JsonParser.parseString(Files.readString(Path.of(args[0]))).getAsJsonObject(),
            "cutscenes", CinematicsRegistry::parseEvent);
        var scene = parsed.toCutscene();
        if (scene.durationTicks != 200 || scene.events.size() != 2 || scene.cameraPath == null
                || scene.cameraPath.getPoints().size() != 4 || scene.cameraPath.getLength() != 190)
            throw new IllegalStateException("Intro duration, events, or camera path did not survive native parsing");
        System.out.println("Native Lumiera parser: " + scene.id + ", " + scene.durationTicks + " ticks, " + scene.events.size() + " events, four camera points through tick " + scene.cameraPath.getLength() + ", " + scene.cameraPositionMode);
    }
}
