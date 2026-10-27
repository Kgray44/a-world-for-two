package worldfortwo.bridge;

import java.io.IOException;
import java.io.InputStream;
import java.net.JarURLConnection;
import java.net.URL;
import java.security.MessageDigest;
import java.util.HexFormat;
import java.util.IdentityHashMap;
import java.util.List;
import java.util.Set;
import org.objectweb.asm.ClassReader;
import org.objectweb.asm.ClassWriter;
import org.objectweb.asm.Opcodes;
import org.objectweb.asm.tree.AbstractInsnNode;
import org.objectweb.asm.tree.ClassNode;
import org.objectweb.asm.tree.FrameNode;
import org.objectweb.asm.tree.LineNumberNode;
import org.objectweb.asm.tree.LabelNode;
import org.objectweb.asm.tree.MethodNode;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.spongepowered.asm.mixin.extensibility.IMixinConfigPlugin;
import org.spongepowered.asm.mixin.extensibility.IMixinInfo;

/** Preserve Registrate's exact registration/callback bodies while serializing per-owner writes.
 * The JVM owns monitor acquisition and exception-safe release; no registry is altered here.
 */
public final class RegistrateConcurrencyPlugin implements IMixinConfigPlugin {
    public static final String TARGET = "com.tterrag.registrate.AbstractRegistrate";
    public static final String MIXIN = "worldfortwo.bridge.mixin.RegistrateConstructionMixin";
    public static final String RESOURCE = "com/tterrag/registrate/AbstractRegistrate.class";
    public static final String DESCRIPTOR = "(Ljava/lang/String;Lnet/minecraft/resources/ResourceKey;Lcom/tterrag/registrate/builders/Builder;Lcom/tterrag/registrate/util/nullness/NonNullSupplier;Lcom/tterrag/registrate/util/nullness/NonNullFunction;)Lcom/tterrag/registrate/util/entry/RegistryEntry;";
    public static final String CALLBACK_DESCRIPTOR = "(Ljava/lang/String;Lnet/minecraft/resources/ResourceKey;Lcom/tterrag/registrate/util/nullness/NonNullConsumer;)Lcom/tterrag/registrate/AbstractRegistrate;";
    private static final String ARCHIVE = "Registrate-MC1.21-1.3.0+67.jar";
    private static final String CLASS_SHA256 = "f23f30cdb05c82faaa4f3fba01f8fb11873557c91b198b0a07d52b8981a925fa";
    private static final String ARCHIVE_SHA256 = "510f4041c41739f1d8ea8850ab8364d3e3a5fada8529beed5d9f479e2523db52";
    private static final Logger LOG = LoggerFactory.getLogger("AWFT-Registrate-Construction");

    @Override public void onLoad(String mixinPackage) {}
    @Override public String getRefMapperConfig() { return null; }
    @Override public boolean shouldApplyMixin(String targetClassName, String mixinClassName) { return true; }
    @Override public void acceptTargets(Set<String> mine, Set<String> others) {}
    @Override public List<String> getMixins() { return null; }
    @Override public void preApply(String targetClassName, ClassNode targetClass, String mixinClassName, IMixinInfo info) {}

    @Override public void postApply(String targetClassName, ClassNode targetClass, String mixinClassName, IMixinInfo info) {
        if (!MIXIN.equals(mixinClassName)) return;
        if (!TARGET.equals(targetClassName)) throw new IllegalStateException("Unexpected Registrate construction target");
        URL original = RegistrateConcurrencyPlugin.class.getClassLoader().getResource(RESOURCE);
        try {
            String body = synchronizeExact(targetClass, original);
            LOG.info("Pinned Registrate +67 accept and addRegisterCallback now share their native per-instance JVM monitor; original body SHA256 witnesses {}", body);
        } catch (IOException failure) {
            throw new IllegalStateException("Cannot verify original pinned Registrate registration writer", failure);
        }
    }

    /** Shared by the real mixin plugin and the standalone exact-class regression fixture. */
    public static String synchronizeExact(ClassNode target, URL original) throws IOException {
        if (original == null) throw new IllegalStateException("Original Registrate class resource is unavailable");
        String origin = original.toExternalForm().replace("%2B", "+").replace("%2b", "+");
        if (!origin.contains(ARCHIVE + "!") && !origin.contains(ARCHIVE + "%23") && !origin.contains(ARCHIVE + "#"))
            throw new IllegalStateException("Registrate registration writer has an unrecognized archive origin");
        byte[] bytes;
        try (InputStream stream = original.openStream()) { bytes = bounded(stream, 262144); }
        if (!CLASS_SHA256.equals(sha(bytes))) throw new IllegalStateException("Original Registrate +67 class digest differs");
        // Plain jar URLs expose the complete source archive. NeoForge union URLs
        // retain the exact nested archive origin and the complete class digest above.
        if (original.openConnection() instanceof JarURLConnection connection) {
            try (InputStream stream = connection.getJarFileURL().openStream()) {
                byte[] archive = bounded(stream, 262144);
                if (archive.length != 181448 || !ARCHIVE_SHA256.equals(sha(archive)))
                    throw new IllegalStateException("Original Registrate +67 archive digest differs");
            }
        }
        ClassNode pinned = new ClassNode();
        new ClassReader(bytes).accept(pinned, 0);
        if (!TARGET.replace('.', '/').equals(target.name) || !pinned.superName.equals(target.superName))
            throw new IllegalStateException("Registrate registration target identity differs");
        MethodNode accept = exact(target, "accept", DESCRIPTOR);
        MethodNode callback = exact(target, "addRegisterCallback", CALLBACK_DESCRIPTOR);
        String acceptBody = verifyMethod(pinned, accept, Opcodes.ACC_PROTECTED);
        String callbackBody = verifyMethod(pinned, callback, Opcodes.ACC_PUBLIC);
        // Validate BOTH methods before mutating either. These non-static methods
        // therefore use exactly the same owner monitor, including the gap between
        // the original callback drain and registration publication in accept().
        accept.access |= Opcodes.ACC_SYNCHRONIZED;
        callback.access |= Opcodes.ACC_SYNCHRONIZED;
        return "accept=" + acceptBody + ", addRegisterCallback=" + callbackBody;
    }

    private static String verifyMethod(ClassNode pinned, MethodNode actual, int flags) {
        MethodNode expected = exact(pinned, actual.name, actual.desc);
        if (actual.access != flags || expected.access != flags)
            throw new IllegalStateException("Registrate " + actual.name + " access flags differ");
        String body = bodyDigest(expected);
        if (!body.equals(bodyDigest(actual)))
            throw new IllegalStateException("Registrate " + actual.name + " was modified before the concurrency repair");
        return body;
    }

    private static MethodNode exact(ClassNode node, String name, String descriptor) {
        List<MethodNode> matches = node.methods.stream().filter(method -> method.name.equals(name) && method.desc.equals(descriptor)).toList();
        if (matches.size() != 1) throw new IllegalStateException("Exactly one Registrate " + name + " method with the pinned descriptor is required");
        return matches.getFirst();
    }

    private static String bodyDigest(MethodNode method) {
        // Encode executable instructions, operands and exception handlers using a
        // fresh constant pool. Debug labels/frames and computed maxs are immaterial.
        ClassWriter writer = new ClassWriter(0);
        writer.visit(Opcodes.V21, Opcodes.ACC_PUBLIC, "awft/RegistrateMethodWitness", null, "java/lang/Object", null);
        var visitor = writer.visitMethod(method.access, method.name, method.desc, null,
            method.exceptions == null ? null : method.exceptions.toArray(String[]::new));
        var labels = new IdentityHashMap<LabelNode, LabelNode>();
        for (AbstractInsnNode instruction : method.instructions)
            if (instruction instanceof LabelNode label) labels.put(label, new LabelNode());
        visitor.visitCode();
        method.tryCatchBlocks.forEach(block -> visitor.visitTryCatchBlock(labels.get(block.start).getLabel(),
            labels.get(block.end).getLabel(), labels.get(block.handler).getLabel(), block.type));
        for (AbstractInsnNode instruction : method.instructions)
            if (!(instruction instanceof FrameNode) && !(instruction instanceof LineNumberNode)) instruction.clone(labels).accept(visitor);
        visitor.visitMaxs(0, 0);
        visitor.visitEnd();
        writer.visitEnd();
        return sha(writer.toByteArray());
    }

    private static byte[] bounded(InputStream stream, int limit) throws IOException {
        byte[] bytes = stream.readNBytes(limit + 1);
        if (bytes.length > limit) throw new IOException("Pinned Registrate resource exceeds its finite byte bound");
        return bytes;
    }

    private static String sha(byte[] bytes) {
        try { return HexFormat.of().formatHex(MessageDigest.getInstance("SHA-256").digest(bytes)); }
        catch (java.security.NoSuchAlgorithmException impossible) { throw new AssertionError(impossible); }
    }
}
