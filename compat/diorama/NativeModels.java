import java.nio.file.Files;
import java.nio.file.Path;
import org.objectweb.asm.ClassReader;
import org.objectweb.asm.ClassWriter;
import org.objectweb.asm.Opcodes;
import org.objectweb.asm.tree.*;

/** Exact NeoForge 1.21.1 call-site repair; no Minecraft classes needed at build time. */
public class NativeModels {
    static final String MODEL = "net/minecraft/client/resources/model/BakedModel";
    static final String EXTENSION = "net/neoforged/neoforge/client/extensions/IBakedModelExtension";
    static final String DATA = "net/neoforged/neoforge/client/model/data/ModelData";
    static final String QUADS = "(Lnet/minecraft/world/level/block/state/BlockState;Lnet/minecraft/core/Direction;Lnet/minecraft/util/RandomSource;)Ljava/util/List;";
    static final String PARTICLE = "()Lnet/minecraft/client/renderer/texture/TextureAtlasSprite;";

    public static void main(String[] args) throws Exception {
        ClassNode node = new ClassNode();
        new ClassReader(Files.readAllBytes(Path.of(args[0]))).accept(node, 0);
        boolean part = node.name.equals("dev/diorama/bake/BlockLooks$LegacyPart");
        if (!part && !node.name.equals("dev/diorama/bake/BlockLooks"))
            throw new IllegalStateException("Unreviewed class");
        int changed = 0;
        for (MethodNode method : node.methods) {
            for (AbstractInsnNode insn : method.instructions.toArray()) {
                if (!(insn instanceof MethodInsnNode call) || !call.owner.equals(MODEL)) continue;
                boolean quads = part && method.name.equals("getQuads") && call.name.equals("getQuads") && call.desc.equals(QUADS);
                boolean particle = !part && method.name.equals("build") && call.name.equals("getParticleIcon") && call.desc.equals(PARTICLE);
                if (!quads && !particle) continue;
                if (call.getOpcode() != Opcodes.INVOKEINTERFACE || !call.itf)
                    throw new IllegalStateException("Unexpected model call opcode");
                InsnList extra = new InsnList();
                extra.add(new FieldInsnNode(Opcodes.GETSTATIC, DATA, "EMPTY", "L" + DATA + ";"));
                if (quads) extra.add(new InsnNode(Opcodes.ACONST_NULL));
                method.instructions.insertBefore(call, extra);
                call.owner = EXTENSION;
                call.desc = quads ? QUADS.replace(")", "L" + DATA + ";Lnet/minecraft/client/renderer/RenderType;)")
                    : "(L" + DATA + ";)Lnet/minecraft/client/renderer/texture/TextureAtlasSprite;";
                changed++;
            }
        }
        if (changed != 1) throw new IllegalStateException("Expected exactly one reviewed call site, found " + changed);
        ClassWriter writer = new ClassWriter(ClassWriter.COMPUTE_MAXS);
        node.accept(writer);
        Files.write(Path.of(args[1]), writer.toByteArray());
    }
}
