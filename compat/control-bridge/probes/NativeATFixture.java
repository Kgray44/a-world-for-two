import java.nio.file.Files;
import java.nio.file.Path;
import java.util.TreeSet;
import java.util.zip.ZipFile;
import net.neoforged.accesstransformer.api.AccessTransformerEngine;
import org.objectweb.asm.ClassReader;
import org.objectweb.asm.ClassWriter;
import org.objectweb.asm.Type;
import org.objectweb.asm.tree.ClassNode;

/** Apply the installed NeoForge access rules in a fresh standalone fixture folder.
 * Never changes the installed named runtime or any mod JAR.
 */
public final class NativeATFixture {
    public static void main(String[] args) throws Exception {
        if (args.length != 3) throw new IllegalArgumentException("named-runtime.jar official-at.cfg fresh-output-folder");
        Path output = Path.of(args[2]).toAbsolutePath().normalize();
        if (Files.exists(output)) throw new IllegalArgumentException("Fixture output must be a new owned folder");
        Path config = Path.of(args[1]);
        if (Files.size(config) > 262144) throw new IllegalArgumentException("AT input exceeds finite bound");
        var names = new TreeSet<String>();
        for (String line : Files.readAllLines(config)) {
            String value = line.split("#", 2)[0].trim();
            if (value.isEmpty()) continue;
            String[] words = value.split("\\s+");
            if (words.length > 1 && words[1].startsWith("net.minecraft.") && words[1].matches("[A-Za-z0-9_.$]+"))
                names.add(words[1].replace('.', '/') + ".class");
        }
        if (names.size() > 512) throw new IllegalArgumentException("AT class set exceeds finite bound");
        var engine = AccessTransformerEngine.newEngine();
        engine.loadATFromPath(config);
        Files.createDirectories(output);
        long written = 0;
        int count = 0;
        try (var archive = new ZipFile(args[0])) {
            for (String name : names) {
                var entry = archive.getEntry(name);
                if (entry == null) continue; // Client-only entries are absent in the dedicated named runtime.
                byte[] raw;
                try (var stream = archive.getInputStream(entry)) { raw = stream.readNBytes(1048577); }
                if (raw.length > 1048576) throw new IllegalArgumentException("A fixture class exceeds finite bound");
                var node = new ClassNode();
                new ClassReader(raw).accept(node, 0);
                engine.transform(node, Type.getObjectType(node.name));
                var writer = new ClassWriter(0);
                node.accept(writer);
                byte[] transformed = writer.toByteArray();
                written += transformed.length;
                if (written > 8388608) throw new IllegalArgumentException("AT output exceeds finite bound");
                Path target = output.resolve(name).normalize();
                if (!target.startsWith(output)) throw new IllegalArgumentException("Fixture target escapes owned output");
                Files.createDirectories(target.getParent());
                Files.write(target, transformed);
                count++;
            }
        }
        System.out.println("Applied original NeoForge AT to " + count + " private fixture classes; " + written + " bytes");
    }
}
