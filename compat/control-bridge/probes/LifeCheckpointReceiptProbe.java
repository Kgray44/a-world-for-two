package worldfortwo.bridge;
import com.google.gson.*;

/** Exercises the actual compiled proposed nested policy without a game. */
public final class LifeCheckpointReceiptProbe {
    static final String C=NativeHabitatLifeSupport.CheckpointReceipt.CANONICAL,L=NativeHabitatLifeSupport.CheckpointReceipt.LIFE;
    static JsonObject json(String value){return JsonParser.parseString(value).getAsJsonObject();}
    static JsonObject canonical(){return json("{\"verified\":true,\"id\":\"20261028T191243Z-6ad3a8\",\"sha256\":\"0ba7ad2097fb52273a37da6a76d8fc030133b79cd26d81b97531d8d74c2546c2\"}");}
    static JsonObject retained(){
        JsonObject b=json("{\"format\":\"awft-life-retained-checkpoint:1\",\"verified\":true,\"id\":\"20261029T140000Z-abc123\"}");
        b.addProperty("sha256","a".repeat(64));JsonObject ref=new JsonObject();ref.addProperty("path",C);ref.addProperty("bytes",200);ref.addProperty("sha256","b".repeat(64));b.add("source_custody",ref);return b;
    }
    static void check(JsonObject b,JsonObject c,String id,String sha,String selector){NativeHabitatLifeSupport.CheckpointReceipt.validate(L,selector,b,id,sha,c);}
    static void refused(Runnable test){try{test.run();}catch(RuntimeException expected){return;}throw new AssertionError("Expected receipt refusal");}
    public static void main(String[] args){
        JsonObject c=canonical(),b=retained();String id=b.get("id").getAsString(),sha=b.get("sha256").getAsString();
        NativeHabitatLifeSupport.CheckpointReceipt.validate(C,"",c,"",c.get("sha256").getAsString(),null);
        check(b,c,id,sha,L);
        if(!NativeHabitatLifeSupport.CheckpointReceipt.habitatBackup(L,c.get("sha256").getAsString(),sha)
            ||!NativeHabitatLifeSupport.CheckpointReceipt.habitatBackup("",sha,sha)
            ||NativeHabitatLifeSupport.CheckpointReceipt.habitatBackup("",c.get("sha256").getAsString(),sha)
            ||NativeHabitatLifeSupport.CheckpointReceipt.habitatBackup(L,"c".repeat(64),sha))
            throw new AssertionError("Fresh habitat verification must retain the exact linked canonical header only");
        refused(()->NativeHabitatLifeSupport.CheckpointReceipt.retained("dashboard/settlement/other.json"));
        refused(()->NativeHabitatLifeSupport.CheckpointReceipt.retained("dashboard/settlement/./life-backup-receipt.json"));
        refused(()->check(b,c,id,sha,""));refused(()->check(b,c,"wrong",sha,L));refused(()->check(b,c,id,"c".repeat(64),L));
        JsonObject bad=b.deepCopy();bad.addProperty("verified",false);refused(()->check(bad,c,id,sha,L));
        JsonObject stringBool=b.deepCopy();stringBool.addProperty("verified","true");refused(()->check(stringBool,c,id,sha,L));
        JsonObject format=b.deepCopy();format.addProperty("format","wrong");refused(()->check(format,c,id,sha,L));
        JsonObject link=b.deepCopy();link.getAsJsonObject("source_custody").addProperty("path",L);refused(()->check(link,c,id,sha,L));
        JsonObject bytes=b.deepCopy();bytes.getAsJsonObject("source_custody").addProperty("bytes",1.5);refused(()->check(bytes,c,id,sha,L));
        JsonObject renamed=c.deepCopy();renamed.addProperty("id","20261029T140000Z-abc123");refused(()->check(b,renamed,id,sha,L));
        JsonObject unverified=c.deepCopy();unverified.addProperty("verified",false);refused(()->check(b,unverified,id,sha,L));
        System.out.println("PASS actual compiled checkpoint receipt policy: legacy, explicit retained identity and rejection cases; no game or archive IO");
    }
}
