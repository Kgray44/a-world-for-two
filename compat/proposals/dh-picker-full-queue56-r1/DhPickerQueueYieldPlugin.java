package worldfortwo.bridge;

import java.io.IOException;
import java.io.InputStream;
import java.net.JarURLConnection;
import java.net.URL;
import java.net.URLDecoder;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
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
import org.objectweb.asm.tree.JumpInsnNode;
import org.objectweb.asm.tree.LabelNode;
import org.objectweb.asm.tree.LineNumberNode;
import org.objectweb.asm.tree.MethodInsnNode;
import org.objectweb.asm.tree.MethodNode;
import org.objectweb.asm.tree.TryCatchBlockNode;
import org.slf4j.LoggerFactory;
import org.spongepowered.asm.mixin.extensibility.IMixinConfigPlugin;
import org.spongepowered.asm.mixin.extensibility.IMixinInfo;

/** Original compatibility transform: retain a rejected task, then release the native picker lock. */
public final class DhPickerQueueYieldPlugin implements IMixinConfigPlugin {
    public static final String TARGET = "com.seibel.distanthorizons.core.util.threading.PriorityTaskPicker";
    public static final String MIXIN = "worldfortwo.bridge.mixin.DhPickerQueueYieldMixin";
    public static final String RESOURCE = TARGET.replace('.', '/') + ".class";
    public static final String ARCHIVE = "DistantHorizons-3.3.3-1.21.1-fabric-neoforge.jar";
    public static final String ARCHIVE_SHA256 = "864e70def5b0d54d619b940b66bb2784e91d3f3fc253064fdc1b3fc5786cbfab";
    public static final String CLASS_SHA256 = "bf5e5df87a4510b92baac14ef5b3a80bbfdcd3718fb4d19eae07b768ea518ee3";
    private static final String LOCK = "java/util/concurrent/locks/ReentrantLock";

    @Override public void onLoad(String mixinPackage) {}
    @Override public String getRefMapperConfig() { return null; }
    @Override public boolean shouldApplyMixin(String target, String mixin) { return true; }
    @Override public void acceptTargets(Set<String> mine, Set<String> others) {}
    @Override public List<String> getMixins() { return null; }
    @Override public void preApply(String target, ClassNode node, String mixin, IMixinInfo info) {}

    @Override public void postApply(String target, ClassNode node, String mixin, IMixinInfo info) {
        if (!MIXIN.equals(mixin)) return;
        if (!TARGET.equals(target)) throw new IllegalStateException("Unexpected DH picker target");
        try {
            String witness = repairExact(node, getClass().getClassLoader().getResource(RESOURCE));
            LoggerFactory.getLogger("AWFT-DH-Picker").info(
                "Pinned DH 3.3.3 rejected-task retry now yields through its original unlock/return; {}", witness);
        } catch (IOException failure) {
            throw new IllegalStateException("Cannot attest the pinned DH picker", failure);
        }
    }

    /** Used unchanged by the real mixin plugin and the isolated exact-native-class reproduction. */
    public static String repairExact(ClassNode target, URL origin) throws IOException {
        if (origin == null) throw new IllegalStateException("Pinned DH class resource is unavailable");
        attestArchive(origin);
        byte[] raw;
        try (InputStream stream = origin.openStream()) { raw = bounded(stream, 16384); }
        if (!CLASS_SHA256.equals(sha(raw))) throw new IllegalStateException("Pinned DH picker class differs");
        ClassNode pinned = new ClassNode();
        new ClassReader(raw).accept(pinned, 0);
        if (!pinned.name.equals(target.name) || !pinned.superName.equals(target.superName))
            throw new IllegalStateException("DH picker class identity differs");
        MethodNode actual = method(target);
        String before = methodDigest(method(pinned));
        if (!before.equals(methodDigest(actual)))
            throw new IllegalStateException("DH startNextTask was modified before this narrow repair");
        List<TryCatchBlockNode> rejections = actual.tryCatchBlocks.stream()
            .filter(block -> "java/util/concurrent/RejectedExecutionException".equals(block.type)).toList();
        if (rejections.size() != 1 || actual.tryCatchBlocks.size() != 3)
            throw new IllegalStateException("DH rejection/finally structure differs");
        TryCatchBlockNode rejected = rejections.getFirst();
        int handler = actual.instructions.indexOf(rejected.handler);
        List<TryCatchBlockNode> finalizers = actual.tryCatchBlocks.stream().filter(block -> block.type == null
            && actual.instructions.indexOf(block.start) < handler
            && actual.instructions.indexOf(block.end) > handler).toList();
        if (finalizers.size() != 1) throw new IllegalStateException("DH outer finally differs");
        LabelNode epilogue = finalizers.getFirst().end;
        AbstractInsnNode ep = next(epilogue);
        if (ep == null || ep.getOpcode() != Opcodes.ALOAD || next(ep).getOpcode() != Opcodes.GETFIELD
            || !(next(next(ep)) instanceof MethodInsnNode unlock) || !LOCK.equals(unlock.owner)
            || !"unlock".equals(unlock.name) || !"()V".equals(unlock.desc))
            throw new IllegalStateException("DH original normal unlock epilogue differs");
        List<MethodInsnNode> adds = java.util.stream.StreamSupport.stream(actual.instructions.spliterator(), false)
            .filter(i -> i instanceof MethodInsnNode).map(i -> (MethodInsnNode)i)
            .filter(i -> "java/util/Queue".equals(i.owner) && "add".equals(i.name)
                && "(Ljava/lang/Object;)Z".equals(i.desc)).toList();
        if (adds.size() != 1 || actual.instructions.indexOf(adds.getFirst()) <= handler)
            throw new IllegalStateException("DH exact rejected-task requeue differs");
        AbstractInsnNode pop = next(adds.getFirst());
        if (pop == null || pop.getOpcode() != Opcodes.POP || !(next(pop) instanceof JumpInsnNode retry)
            || retry.getOpcode() != Opcodes.GOTO || actual.instructions.indexOf(retry.label) >= handler)
            throw new IllegalStateException("DH rejected-task retry branch differs");
        // Every assertion precedes the sole mutation. The native requeue/clear,
        // exception table, counters and finally body remain literal. In particular,
        // do not insert a RETURN inside the try block: that would strand its lock.
        retry.label = epilogue;
        return "before=" + before + ", after=" + methodDigest(actual) + ", changedBranches=1";
    }

    private static AbstractInsnNode next(AbstractInsnNode instruction) {
        do { instruction = instruction.getNext(); }
        while (instruction instanceof LabelNode || instruction instanceof FrameNode || instruction instanceof LineNumberNode);
        return instruction;
    }

    private static MethodNode method(ClassNode node) {
        List<MethodNode> methods = node.methods.stream()
            .filter(m -> "startNextTask".equals(m.name) && "(Z)V".equals(m.desc)).toList();
        if (methods.size() != 1) throw new IllegalStateException("Exact DH startNextTask method is required");
        return methods.getFirst();
    }

    public static String methodDigest(MethodNode method) {
        ClassWriter writer = new ClassWriter(0);
        writer.visit(Opcodes.V21, Opcodes.ACC_PUBLIC, "awft/DhPickerMethodWitness", null, "java/lang/Object", null);
        var visitor = writer.visitMethod(method.access, method.name, method.desc, null,
            method.exceptions == null ? null : method.exceptions.toArray(String[]::new));
        var labels = new IdentityHashMap<LabelNode, LabelNode>();
        for (AbstractInsnNode i : method.instructions) if (i instanceof LabelNode label) labels.put(label, new LabelNode());
        visitor.visitCode();
        method.tryCatchBlocks.forEach(block -> visitor.visitTryCatchBlock(labels.get(block.start).getLabel(),
            labels.get(block.end).getLabel(), labels.get(block.handler).getLabel(), block.type));
        for (AbstractInsnNode i : method.instructions)
            if (!(i instanceof FrameNode) && !(i instanceof LineNumberNode)) i.clone(labels).accept(visitor);
        visitor.visitMaxs(0, 0); visitor.visitEnd(); writer.visitEnd();
        return sha(writer.toByteArray());
    }

    private static void attestArchive(URL origin) throws IOException {
        Path archive;
        try {
            if (origin.openConnection() instanceof JarURLConnection jar) {
                if (!"file".equals(jar.getJarFileURL().getProtocol()))
                    throw new IllegalStateException("DH archive is not a local file");
                archive = Path.of(jar.getJarFileURL().toURI()).toRealPath();
            } else {
                // The actual NeoForge loader exposes resources in its union filesystem.
                // Bind that resource origin to the exact local mods archive as well as
                // pinning the complete original class and full archive content below.
                archive = Path.of(System.getProperty("user.dir"), "mods", ARCHIVE).toRealPath();
                String decoded = URLDecoder.decode(origin.toExternalForm(), StandardCharsets.UTF_8).replace('\\', '/');
                String base = "union:" + archive.toUri().getPath();
                if (!(decoded.startsWith(base + "#") || decoded.startsWith(base + "!")))
                    throw new IllegalStateException("DH union resource is not from the exact local mods archive");
            }
        } catch (java.net.URISyntaxException invalid) { throw new IOException("Invalid DH archive origin", invalid); }
        if (!ARCHIVE.equals(archive.getFileName().toString()) || Files.size(archive) != 28289212)
            throw new IllegalStateException("Pinned DH archive identity differs");
        try (InputStream stream = Files.newInputStream(archive)) {
            MessageDigest digest = MessageDigest.getInstance("SHA-256");
            byte[] chunk = new byte[65536]; int total = 0, n;
            while ((n = stream.read(chunk)) != -1) {
                total += n;
                if (total > 32 * 1024 * 1024) throw new IOException("DH archive exceeds its finite bound");
                digest.update(chunk, 0, n);
            }
            if (!ARCHIVE_SHA256.equals(HexFormat.of().formatHex(digest.digest())))
                throw new IllegalStateException("Pinned DH archive digest differs");
        } catch (java.security.NoSuchAlgorithmException impossible) { throw new AssertionError(impossible); }
    }

    private static byte[] bounded(InputStream stream, int limit) throws IOException {
        byte[] bytes = stream.readNBytes(limit + 1);
        if (bytes.length > limit) throw new IOException("DH class exceeds its finite bound");
        return bytes;
    }

    private static String sha(byte[] bytes) {
        try { return HexFormat.of().formatHex(MessageDigest.getInstance("SHA-256").digest(bytes)); }
        catch (java.security.NoSuchAlgorithmException impossible) { throw new AssertionError(impossible); }
    }
}
