package worldfortwo.bridge;
import com.google.gson.*;
import java.nio.charset.StandardCharsets;
import java.nio.file.*;

/** Exact production parser/ledger, no Minecraft bootstrap or world object. */
public final class NativeRelocationCatalogProbe {
    private static void require(boolean value,String reason){if(!value)throw new AssertionError(reason);}
    private static void refused(JsonObject catalog,String id){boolean no=false;try{NativeRelocationSupport.Capsules.select(catalog,id);}catch(RuntimeException expected){no=true;}require(no,"Invalid capsule admitted");}
    public static void main(String[] args)throws Exception{
        if(args.length!=2)throw new IllegalArgumentException("Exact private catalogue and new owned fixture directory");
        Path input=Path.of(args[0]).toAbsolutePath().normalize(),out=Path.of(args[1]).toAbsolutePath().normalize();
        if(!input.startsWith(Path.of("D:/A World for Two/staging/world-tests"))||!out.startsWith(Path.of("D:/A World for Two/staging"))||!out.getFileName().toString().startsWith("native-relocation-ledger-fixture-r2-")||Files.size(input)>2*1024*1024)throw new IllegalArgumentException("Bounded owned fixture paths only");
        JsonObject original=JsonParser.parseString(Files.readString(input)).getAsJsonObject();int yes=0,no=0;
        for(JsonElement e:original.getAsJsonArray("capsules")){JsonObject r=e.getAsJsonObject();String id=r.get("id").getAsString();if(r.get("supported").getAsBoolean()){NativeRelocationSupport.Capsules.select(original,id);yes++;}else{refused(original,id);no++;}}
        require(yes==92&&no==1,"Actual sealed catalogue membership differs");refused(original,"unknown/room:0");
        String id="eastern22/pippins-net:room:0";
        for(String test:new String[]{"identity","fractional","resized","duplicate"}){
            JsonObject c=original.deepCopy(),r=null;for(JsonElement e:c.getAsJsonArray("capsules"))if(e.getAsJsonObject().get("id").getAsString().equals(id))r=e.getAsJsonObject();
            if(test.equals("identity")){r.add("destination_bounds_xyz",r.get("source_bounds_xyz").deepCopy());r.add("translation_xyz",JsonParser.parseString("[0,0,0]"));}
            if(test.equals("fractional"))r.getAsJsonArray("source_bounds_xyz").set(0,new JsonPrimitive(1236.5));
            if(test.equals("resized"))r.getAsJsonArray("destination_bounds_xyz").set(3,new JsonPrimitive(1231));
            if(test.equals("duplicate"))c.getAsJsonArray("capsules").set(0,r.deepCopy());
            refused(c,id);
        }
        require(NativeRelocationSupport.Capsules.salt(id,-13,0,0).equals("PIPPIN320|-13,0,0"),"Legacy once-only identity was changed");
        Files.createDirectory(out);Path intent=out.resolve("intent.json");byte[] bytes="{\"phase\":\"intent\"}\n".getBytes(StandardCharsets.UTF_8);NativeRelocationSupport.Ledger.create(intent,bytes);
        boolean refused=false;try{NativeRelocationSupport.Ledger.create(intent,bytes);}catch(FileAlreadyExistsException expected){refused=true;}require(refused,"Existing durable intent replayed");
        System.out.println("PASS actual production catalogue92/held1; unknown/identity/fractional/resized/duplicate refusals; legacy ledger salt; real CREATE_NEW+force no replay; no Minecraft operation");
    }
}
