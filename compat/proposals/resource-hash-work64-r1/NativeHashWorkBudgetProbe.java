package worldfortwo.bridge;

import java.io.ByteArrayInputStream;
import java.io.IOException;
import java.io.InputStream;
import java.lang.reflect.Field;
import java.lang.reflect.InvocationTargetException;
import java.lang.reflect.Method;
import java.nio.ByteBuffer;
import java.nio.charset.StandardCharsets;
import java.nio.file.Path;
import java.security.MessageDigest;
import java.util.Arrays;
import java.util.concurrent.atomic.AtomicBoolean;
import net.minecraft.server.packs.resources.IoSupplier;

/** Focused actual production-JAR guard fixture; no client/server/world or large byte allocation. */
public final class NativeHashWorkBudgetProbe {
    private static final Class<?> OWNER=LithostitchedSeedgenResources.class;
    private static final Class<?> ACC=Arrays.stream(OWNER.getDeclaredClasses()).filter(c->c.getSimpleName().equals("Accumulator")).findFirst().orElseThrow();
    private static final int DISTINCT=262144,HASH=1048576;
    private static final long BYTES=2L*1024*1024*1024,RESOURCE=32L*1024*1024;
    private static int checks;
    public static void main(String[] args)throws Throwable {
        if(args.length!=1)throw new IllegalArgumentException("Exact candidate JAR path required");
        check(Path.of(OWNER.getProtectionDomain().getCodeSource().getLocation().toURI()).toRealPath().equals(Path.of(args[0]).toRealPath()),"Production class comes from exact candidate JAR");
        check(constant("MAX_ENTRIES")==DISTINCT&&constant("MAX_HASH_VISITS")==HASH&&constant("MAX_VISITS")==HASH,"Distinct, hash and traversal units are separate and finite");
        check(constant("MAX_PACKS")==512&&constant("MAX_HASH_WORK_BYTES")==BYTES&&constant("MAX_RESOURCE")==RESOURCE,"Pack, per-resource and finite hash-work bounds verified");
        Object acc=fresh();field("entries").setInt(acc,DISTINCT);
        resource(acc,"fixture/repeated-id",null);
        check(field("entries").getInt(acc)==DISTINCT+1,"Repeated hash visit262145 is admitted");
        Method distinct=OWNER.getDeclaredMethod("requireDistinctIds",int.class);distinct.setAccessible(true);
        invoke(distinct,null,DISTINCT);checks++;
        refused(()->invoke(distinct,null,DISTINCT+1),"distinctIds=262145");
        acc=fresh();field("entries").setInt(acc,HASH-1);resource(acc,"fixture/final-hash",null);
        check(field("entries").getInt(acc)==HASH,"Final bounded hash visit admitted");
        final Object full=acc;
        String diagnostic=refused(()->resource(full,"fixture/overflow-hash",null),"hashVisits=1048577");
        check(diagnostic.contains("hashVisitLimit=1048576")&&diagnostic.contains("distinctLimit=262144")&&diagnostic.contains("phase=opened-pack-inventory")&&diagnostic.contains("hashReadWorkBytes=0")&&diagnostic.contains("resource=fixture/overflow-hash"),"Refusal distinguishes hash visits, IDs, phase, bytes and resource");
        acc=fresh();field("bytes").setLong(acc,512L*1024*1024);resource(acc,"fixture/old-work-boundary",()->new ByteArrayInputStream(new byte[]{1}));
        check(field("bytes").getLong(acc)==512L*1024*1024+1,"Repeated hash work beyond old512MiB is admitted without retained allocation");
        acc=fresh();field("bytes").setLong(acc,BYTES-1);resource(acc,"fixture/final-byte",()->new ByteArrayInputStream(new byte[]{1}));
        check(field("bytes").getLong(acc)==BYTES,"Exact finite2GiB cumulative hash-work bound admitted");
        final Object fullBytes=acc;
        refused(()->resource(fullBytes,"fixture/byte-overflow",()->new ByteArrayInputStream(new byte[]{1})),"hashReadWorkLimit=2147483648");
        acc=fresh();resource(acc,"fixture/exact-resource",()->new FiniteZeros(RESOURCE));
        check(field("bytes").getLong(acc)==RESOURCE,"Exact32MiB per-resource bound admitted without allocating32MiB");
        final Object perResource=fresh();
        refused(()->resource(perResource,"fixture/resource-overflow",()->new FiniteZeros(RESOURCE+1)),"resourceLimit=33554432");
        final Object expired=fresh();field("deadline").setLong(expired,System.nanoTime()-1);AtomicBoolean opened=new AtomicBoolean();
        refused(()->resource(expired,"fixture/expired",()->{opened.set(true);return InputStream.nullInputStream();}),"finite deadline");
        check(!opened.get(),"Deadline refuses before source open");
        final Object traversal=fresh();field("visits").setInt(traversal,HASH);Method visit=ACC.getDeclaredMethod("visit");visit.setAccessible(true);
        refused(()->invoke(visit,traversal),"traversalVisits=1048577");
        acc=fresh();byte[] data={3,1,4,1,5};resource(acc,"fixture/same-bytes",()->new ByteArrayInputStream(data));
        MessageDigest expected=MessageDigest.getInstance("SHA-256");byte[] id="fixture/same-bytes".getBytes(StandardCharsets.UTF_8);
        number(expected,id.length);expected.update(id);number(expected,1);number(expected,data.length);expected.update(MessageDigest.getInstance("SHA-256").digest(data));
        check(Arrays.equals(expected.digest(),((MessageDigest)field("digest").get(acc)).digest()),"Legacy hash feed bytes and order unchanged");
        check(OWNER.getRecordComponents()==null,"Production owner remains ordinary final class");
        check(Arrays.stream(LithostitchedSeedgenResources.Attestation.class.getRecordComponents()).map(c->c.getName()).toList().equals(java.util.List.of("orderedPacks","sha256","entries","bytes")),"Attestation record ABI preserved");
        System.out.println("PROBE_RESULT {\"passed\":true,\"checks\":"+checks+",\"old512MiB_hash_work_boundary_admitted\":true,\"finite2GiB_hash_work_boundary_enforced\":true,\"hash262145_admitted\":true,\"distinct262145_refused\":true,\"hash1048577_refused\":true,\"per_resource_time_traversal_limits_preserved\":true,\"digest_feed_unchanged\":true,\"world_started\":false}");
    }
    private static long constant(String name)throws Exception {Field f=OWNER.getDeclaredField(name);f.setAccessible(true);return ((Number)f.get(null)).longValue();}
    private static Object fresh()throws Exception {var c=ACC.getDeclaredConstructor();c.setAccessible(true);return c.newInstance();}
    private static Field field(String name)throws Exception {Field f=ACC.getDeclaredField(name);f.setAccessible(true);return f;}
    private static Object resource(Object acc,String id,IoSupplier<InputStream> source)throws Throwable {Method m=ACC.getDeclaredMethod("resource",String.class,IoSupplier.class);m.setAccessible(true);return invoke(m,acc,id,source);}
    private static Object invoke(Method m,Object target,Object... args)throws Throwable {try{return m.invoke(target,args);}catch(InvocationTargetException e){throw e.getCause();}}
    private static void number(MessageDigest d,long n){d.update(ByteBuffer.allocate(Long.BYTES).putLong(n).array());}
    private static void check(boolean pass,String message){if(!pass)throw new AssertionError(message);checks++;}
    @FunctionalInterface private interface Checked {void run()throws Throwable;}
    private static String refused(Checked action,String detail)throws Throwable {try{action.run();throw new AssertionError("Expected refusal: "+detail);}catch(IOException expected){check(expected.getMessage().contains(detail),"Precise refusal: "+detail);return expected.getMessage();}}
    private static final class FiniteZeros extends InputStream {
        private long remaining;FiniteZeros(long size){remaining=size;}
        @Override public int read(){if(remaining==0)return -1;remaining--;return 0;}
        @Override public int read(byte[] b,int off,int len){if(remaining==0)return -1;if(len==0)return 0;int n=(int)Math.min(remaining,len);Arrays.fill(b,off,off+n,(byte)0);remaining-=n;return n;}
    }
}
