import java.net.URL;
import java.nio.file.Files;
import java.nio.file.Path;
import org.objectweb.asm.ClassReader;
import org.objectweb.asm.ClassWriter;
import org.objectweb.asm.Opcodes;
import org.objectweb.asm.tree.ClassNode;
import org.objectweb.asm.tree.InsnNode;
import org.objectweb.asm.tree.MethodNode;
import worldfortwo.bridge.RegistrateConcurrencyPlugin;

/** Calls the production transformation; no copied Registrate implementation. */
public final class TransformPinnedRegistrate {
    static byte[] raw;
    static ClassNode fresh() {
        var node = new ClassNode();
        new ClassReader(raw).accept(node, 0);
        return node;
    }
    static MethodNode method(ClassNode node, boolean callback) {
        String name = callback ? "addRegisterCallback" : "accept";
        String descriptor = callback ? RegistrateConcurrencyPlugin.CALLBACK_DESCRIPTOR : RegistrateConcurrencyPlugin.DESCRIPTOR;
        return node.methods.stream().filter(m -> m.name.equals(name) && m.desc.equals(descriptor)).findFirst().orElseThrow();
    }
    interface Check { void run() throws Exception; }
    static void rejects(String name, Check check) throws Exception {
        try {
            check.run();
            throw new AssertionError("Accepted " + name);
        } catch (IllegalStateException expected) { System.out.println("PASS rejects " + name); }
    }
    static void guardCases(URL origin, boolean callback) throws Exception {
        String name = callback ? "callback" : "accept";
        rejects("modified " + name + " body", () -> {
            var node = fresh();
            method(node, callback).instructions.insert(new InsnNode(Opcodes.NOP));
            try { RegistrateConcurrencyPlugin.synchronizeExact(node, origin); }
            finally {
                if ((method(node, false).access & Opcodes.ACC_SYNCHRONIZED) != 0)
                    throw new AssertionError("Rejected guard partially changed accept flags");
                if ((method(node, true).access & Opcodes.ACC_SYNCHRONIZED) != 0)
                    throw new AssertionError("Rejected guard partially changed callback flags");
            }
        });
        rejects("wrong " + name + " flags", () -> {
            var node = fresh();
            method(node, callback).access |= Opcodes.ACC_STATIC;
            RegistrateConcurrencyPlugin.synchronizeExact(node, origin);
        });
        rejects("duplicate " + name + " descriptor", () -> {
            var node = fresh();
            var original = method(node, callback);
            node.methods.add(new MethodNode(original.access, original.name, original.desc, null, null));
            RegistrateConcurrencyPlugin.synchronizeExact(node, origin);
        });
        rejects("missing " + name + " descriptor", () -> {
            var node = fresh();
            node.methods.remove(method(node, callback));
            RegistrateConcurrencyPlugin.synchronizeExact(node, origin);
        });
    }
    public static void main(String[] args) throws Exception {
        if (args.length != 1) throw new IllegalArgumentException("Fresh output overlay directory required");
        URL origin = TransformPinnedRegistrate.class.getClassLoader().getResource(RegistrateConcurrencyPlugin.RESOURCE);
        try (var stream = origin.openStream()) { raw = stream.readAllBytes(); }
        var node = fresh();
        String bodies = RegistrateConcurrencyPlugin.synchronizeExact(node, origin);
        if (method(node, false).access != (Opcodes.ACC_PROTECTED | Opcodes.ACC_SYNCHRONIZED)
                || method(node, true).access != (Opcodes.ACC_PUBLIC | Opcodes.ACC_SYNCHRONIZED))
            throw new AssertionError("Unexpected method flags");
        var writer = new ClassWriter(0);
        node.accept(writer);
        Path output = Path.of(args[0]).resolve(RegistrateConcurrencyPlugin.RESOURCE);
        Files.createDirectories(output.getParent());
        if (Files.exists(output)) throw new IllegalStateException("Refusing to overwrite an existing fixture overlay");
        Files.write(output, writer.toByteArray());
        System.out.println("PASS production transform originalBodiesSHA256=" + bodies + " origin=" + origin.getProtocol()
            + " acceptFlags4to36 callbackFlags1to33");
        guardCases(origin, false);
        guardCases(origin, true);
        rejects("wrong archive origin", () -> RegistrateConcurrencyPlugin.synchronizeExact(fresh(),
            new URL("jar:file:/nonexistent/other.jar!/" + RegistrateConcurrencyPlugin.RESOURCE)));
        rejects("missing resource", () -> RegistrateConcurrencyPlugin.synchronizeExact(fresh(), null));
    }
}
