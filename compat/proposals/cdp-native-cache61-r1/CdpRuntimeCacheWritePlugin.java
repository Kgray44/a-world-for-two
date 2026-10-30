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
import org.objectweb.asm.tree.*;
import org.slf4j.LoggerFactory;
import org.spongepowered.asm.mixin.extensibility.IMixinConfigPlugin;
import org.spongepowered.asm.mixin.extensibility.IMixinInfo;

/** Exact native cache-write body, with its existing resources map as the sole monitor. */
public final class CdpRuntimeCacheWritePlugin implements IMixinConfigPlugin {
    public static final String TARGET="plus.dragons.createdragonsplus.data.runtime.RuntimePackResources";
    public static final String MIXIN="worldfortwo.bridge.mixin.CdpRuntimeCacheWriteMixin";
    public static final String RESOURCE=TARGET.replace('.','/')+".class";
    public static final String ARCHIVE="CreateDragonsPlus-1.11.9.jar";
    public static final String ARCHIVE_SHA256="37f05a6775bbe811fe8c2833fa6289a1c704d0b25bdd5f239d343a5c6f62ed8a";
    public static final String CLASS_SHA256="05098526debde24c618391bd8c1eeaa3b285eeff290371aeedfc0602d532a244";
    public static final String WRITE_DESCRIPTOR="(Ljava/nio/file/Path;[BLcom/google/common/hash/HashCode;)V";
    @Override public void onLoad(String name) {}
    @Override public String getRefMapperConfig(){return null;}
    @Override public boolean shouldApplyMixin(String target,String mixin){return true;}
    @Override public void acceptTargets(Set<String> mine,Set<String> others){}
    @Override public List<String> getMixins(){return null;}
    @Override public void preApply(String target,ClassNode node,String mixin,IMixinInfo info){}
    @Override public void postApply(String target,ClassNode node,String mixin,IMixinInfo info){
        if(!MIXIN.equals(mixin))return;
        if(!TARGET.equals(target))throw new IllegalStateException("Unexpected CDP cache target");
        try{String proof=repairExact(node,getClass().getClassLoader().getResource(RESOURCE));
            LoggerFactory.getLogger("AWFT-CDP-Cache").info("Pinned native CDP cache writer now holds its existing resources-map monitor; {}",proof);
        }catch(IOException failure){throw new IllegalStateException("Cannot attest pinned CDP cache writer",failure);}
    }

    /** Used by both the production mixin and the isolated actual-class concurrency probe. */
    public static String repairExact(ClassNode target,URL origin)throws IOException {
        if(origin==null)throw new IllegalStateException("Pinned CDP class resource is absent");
        attestArchive(origin);
        byte[] raw;try(InputStream in=origin.openStream()){raw=in.readNBytes(14621);}
        if(raw.length!=14620||!CLASS_SHA256.equals(sha(raw)))throw new IllegalStateException("Pinned CDP class differs");
        ClassNode pinned=new ClassNode();new ClassReader(raw).accept(pinned,0);
        if(!pinned.name.equals(target.name)||!pinned.superName.equals(target.superName))throw new IllegalStateException("CDP class identity differs");
        MethodNode nativeMethod=writer(pinned),method=writer(target);
        String before=methodDigest(nativeMethod);
        if(!before.equals(methodDigest(method)))throw new IllegalStateException("CDP native writer was already modified");
        long maps=target.fields.stream().filter(f->f.name.equals("resources")&&f.desc.equals("Ljava/util/Map;")&&(f.access&Opcodes.ACC_STATIC)==0).count();
        if(maps!=1||method.maxLocals!=4||!method.tryCatchBlocks.isEmpty()||(method.access&Opcodes.ACC_SYNCHRONIZED)!=0)
            throw new IllegalStateException("CDP writer/map shape differs");
        int puts=0,returns=0,resources=0,body=0;AbstractInsnNode ret=null;
        for(AbstractInsnNode i:method.instructions){
            if(i.getOpcode()<0)continue;body++;
            if(i instanceof MethodInsnNode m){
                if(!m.owner.equals("java/util/Map")||!m.name.equals("put")||!m.desc.equals("(Ljava/lang/Object;Ljava/lang/Object;)Ljava/lang/Object;"))
                    throw new IllegalStateException("Unexpected native CDP writer call");
                puts++;
            }
            if(i instanceof FieldInsnNode f){
                if(f.getOpcode()!=Opcodes.GETFIELD||!f.owner.equals(target.name)||!f.name.equals("resources")||!f.desc.equals("Ljava/util/Map;"))
                    throw new IllegalStateException("Unexpected native CDP writer field access");
                resources++;
            }
            if(i.getOpcode()==Opcodes.RETURN){returns++;ret=i;}
        }
        if(puts!=1||returns!=1||resources!=1||body!=8||ret==null||next(ret)!=null)
            throw new IllegalStateException("Exact single native CDP put/return required");
        // All attestation and shape checks precede mutation. No native body instruction is replaced.
        int monitor=4,error=5;LabelNode start=new LabelNode(),end=new LabelNode(),handler=new LabelNode();
        InsnList enter=new InsnList();enter.add(new VarInsnNode(Opcodes.ALOAD,0));
        enter.add(new FieldInsnNode(Opcodes.GETFIELD,target.name,"resources","Ljava/util/Map;"));
        enter.add(new InsnNode(Opcodes.DUP));enter.add(new VarInsnNode(Opcodes.ASTORE,monitor));
        enter.add(new InsnNode(Opcodes.MONITORENTER));enter.add(start);method.instructions.insert(enter);
        InsnList leave=new InsnList();leave.add(end);leave.add(new VarInsnNode(Opcodes.ALOAD,monitor));
        leave.add(new InsnNode(Opcodes.MONITOREXIT));method.instructions.insertBefore(ret,leave);
        method.instructions.add(handler);
        method.instructions.add(new FrameNode(Opcodes.F_FULL,5,new Object[]{target.name,"java/nio/file/Path","[B","com/google/common/hash/HashCode","java/util/Map"},1,new Object[]{"java/lang/Throwable"}));
        method.instructions.add(new VarInsnNode(Opcodes.ASTORE,error));method.instructions.add(new VarInsnNode(Opcodes.ALOAD,monitor));
        method.instructions.add(new InsnNode(Opcodes.MONITOREXIT));method.instructions.add(new VarInsnNode(Opcodes.ALOAD,error));
        method.instructions.add(new InsnNode(Opcodes.ATHROW));method.tryCatchBlocks.add(new TryCatchBlockNode(start,end,handler,null));
        method.maxLocals=6;method.maxStack=Math.max(method.maxStack,2);
        return "before="+before+", after="+methodDigest(method)+", nativeBodyInstructionsRetained=8, monitor=resources";
    }
    private static AbstractInsnNode next(AbstractInsnNode n){do{n=n.getNext();}while(n instanceof LabelNode||n instanceof FrameNode||n instanceof LineNumberNode);return n;}
    private static MethodNode writer(ClassNode node){
        var matches=node.methods.stream().filter(m->m.name.equals("writeIfNeeded")&&m.desc.equals(WRITE_DESCRIPTOR)).toList();
        if(matches.size()!=1)throw new IllegalStateException("Exact CDP writeIfNeeded method required");return matches.getFirst();
    }
    public static String methodDigest(MethodNode method){
        ClassWriter writer=new ClassWriter(0);writer.visit(Opcodes.V21,Opcodes.ACC_PUBLIC,"awft/CdpWriterWitness",null,"java/lang/Object",null);
        var v=writer.visitMethod(method.access,method.name,method.desc,null,method.exceptions==null?null:method.exceptions.toArray(String[]::new));
        var labels=new IdentityHashMap<LabelNode,LabelNode>();for(AbstractInsnNode i:method.instructions)if(i instanceof LabelNode l)labels.put(l,new LabelNode());
        v.visitCode();for(var t:method.tryCatchBlocks)v.visitTryCatchBlock(labels.get(t.start).getLabel(),labels.get(t.end).getLabel(),labels.get(t.handler).getLabel(),t.type);
        for(AbstractInsnNode i:method.instructions)if(!(i instanceof FrameNode)&&!(i instanceof LineNumberNode))i.clone(labels).accept(v);
        v.visitMaxs(0,0);v.visitEnd();writer.visitEnd();return sha(writer.toByteArray());
    }
    private static void attestArchive(URL origin)throws IOException {
        Path archive;
        try{
            if(origin.openConnection() instanceof JarURLConnection jar){
                if(!jar.getJarFileURL().getProtocol().equals("file"))throw new IllegalStateException("CDP archive must be local");
                archive=Path.of(jar.getJarFileURL().toURI()).toRealPath();
            }else{
                archive=Path.of(System.getProperty("user.dir"),"mods",ARCHIVE).toRealPath();
                String actual=URLDecoder.decode(origin.toExternalForm(),StandardCharsets.UTF_8).replace('\\','/');
                String expected="union:"+archive.toUri().getPath();
                if(!(actual.startsWith(expected+"#")||actual.startsWith(expected+"!")))throw new IllegalStateException("CDP union origin differs");
            }
        }catch(java.net.URISyntaxException invalid){throw new IOException("Invalid CDP resource origin",invalid);}
        if(!archive.getFileName().toString().equals(ARCHIVE)||Files.size(archive)!=1085674L)throw new IllegalStateException("Pinned CDP archive identity differs");
        try(InputStream in=Files.newInputStream(archive)){
            byte[] bytes=in.readNBytes(1085675);if(bytes.length!=1085674||!sha(bytes).equals(ARCHIVE_SHA256))throw new IllegalStateException("Pinned CDP archive digest differs");
        }
    }
    private static String sha(byte[] bytes){try{return HexFormat.of().formatHex(MessageDigest.getInstance("SHA-256").digest(bytes));}catch(java.security.NoSuchAlgorithmException impossible){throw new AssertionError(impossible);}}
}
