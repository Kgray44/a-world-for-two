package worldfortwo.bridge;
import com.google.gson.*;
import java.util.*;

/** Synthetic source-authority fixtures only; not a native world or physical pass. */
public final class TownLifeAuthorityProbe {
    private static int cases;
    private static final Gson JSON=new Gson();
    private static JsonArray array(int... values){JsonArray a=new JsonArray();for(int v:values)a.add(v);return a;}
    private static JsonArray strings(String... values){JsonArray a=new JsonArray();for(String v:values)a.add(v);return a;}
    private static JsonObject fixture(){
        JsonObject d=new JsonObject();d.addProperty("format","awft-town-life-authority:1");d.addProperty("seed","FIXTURE");d.addProperty("world_path","FIXTURE");d.addProperty("source_checkpoint_sha256","a".repeat(64));
        JsonObject source=new JsonObject();source.addProperty("name","signal-lane-full");source.addProperty("kind","AUTHORED_FULL_PLAN");
        JsonObject ref=new JsonObject();ref.addProperty("path","fixture-plan.json");ref.addProperty("bytes",4000);ref.addProperty("sha256","b".repeat(64));source.add("plan",ref);
        JsonObject verify=ref.deepCopy();verify.addProperty("path","fixture-verify.json");source.add("native_verify",verify);JsonArray sources=new JsonArray();sources.add(source);d.add("sources",sources);
        JsonObject site=new JsonObject();site.addProperty("id","chandler-home");site.add("source_names",strings("signal-lane-full"));site.add("species",strings("cozys-improved-cats:improved_cat","ribbits:ribbit","minecraft:villager","doggytalents:dog"));site.add("known_bounds",array(1246,65,-1266,1250,69,-1262));
        JsonArray cells=new JsonArray();for(int x=1246;x<=1250;x++)for(int z=-1266;z<=-1262;z++)for(int y=65;y<=69;y++)cells.add(array(x,y,z));site.add("occupancy_cells",cells);JsonArray standing=new JsonArray();standing.add(array(1248,66,-1264));standing.add(array(1249,66,-1264));site.add("standing_positions",standing);JsonArray sites=new JsonArray();sites.add(site);d.add("sites",sites);return d;
    }
    private static JsonObject plan(){JsonObject p=new JsonObject();p.addProperty("format","awft-native-settlement:1");p.addProperty("seed","FIXTURE");p.addProperty("world_path","FIXTURE");p.add("palette",strings("minecraft:stone","minecraft:air"));JsonArray rows=new JsonArray();for(int x=1246;x<=1250;x++)for(int z=-1266;z<=-1262;z++)for(int y=65;y<=69;y++)rows.add(array(x,y,z,y==65?0:1));p.add("blocks",rows);return p;}
    private static JsonObject proof(){JsonObject p=new JsonObject();p.addProperty("operation","verify");p.addProperty("plan_sha256","b".repeat(64));p.addProperty("blocks",125);p.addProperty("failures",0);p.addProperty("status","verified actual block identities, orientation, block entities and supplied inventories");return p;}
    private static TownLifeAuthority authority(JsonObject doc,JsonObject source,JsonObject proof)throws Exception{return new TownLifeAuthority(doc,"FIXTURE","FIXTURE","a".repeat(64),(ref,cap)->ref.get("path").getAsString().contains("verify")?proof:source,ref->{});}
    @FunctionalInterface private interface Work{void run()throws Exception;}
    private static void yes(Work work)throws Exception{work.run();cases++;}
    private static void no(Work work)throws Exception{try{work.run();}catch(IllegalStateException expected){cases++;return;}throw new AssertionError("Expected authority refusal");}
    public static void main(String[] ignored)throws Exception{
        TownLifeAuthority a=authority(fixture(),plan(),proof());HabitatLifePolicy.Box known=new HabitatLifePolicy.Box(1246,65,-1266,1250,69,-1262);
        yes(()->a.site("chandler-home").member("ribbits:ribbit",known,1248.5,66,-1263.5));
        yes(()->a.site("chandler-home").cell(1248,67,-1264));yes(()->a.site("chandler-home").standing(1249,66,-1264));
        no(()->HabitatLifePolicy.coordinate(1248.5,66,-1263.5));yes(()->HabitatLifePolicy.coordinateTown(1248.5,66,-1263.5));
        no(()->a.site("invented-room"));no(()->a.site("chandler-home").member("naturalist:deer",known,1248.5,66,-1263.5));
        no(()->a.site("chandler-home").standing(1246,66,-1264));no(()->a.site("chandler-home").cell(1251,67,-1264));
        no(()->a.site("chandler-home").member("ribbits:ribbit",new HabitatLifePolicy.Box(1245,65,-1266,1250,69,-1262),1248.5,66,-1263.5));
        JsonObject bad=fixture();bad.addProperty("source_checkpoint_sha256","c".repeat(64));no(()->authority(bad,plan(),proof()));
        JsonObject foreign=plan();foreign.addProperty("seed","OTHER");no(()->authority(fixture(),foreign,proof()));
        JsonObject failed=proof();failed.addProperty("failures",1);no(()->authority(fixture(),plan(),failed));
        JsonObject stale=proof();stale.addProperty("plan_sha256","c".repeat(64));no(()->authority(fixture(),plan(),stale));
        JsonObject tickets=proof();tickets.addProperty("temporary_tickets_remaining",1);no(()->authority(fixture(),plan(),tickets));
        JsonObject invented=fixture();invented.getAsJsonArray("sites").get(0).getAsJsonObject().getAsJsonArray("occupancy_cells").add(array(1251,67,-1264));no(()->authority(invented,plan(),proof()));
        JsonObject trait=fixture();trait.getAsJsonArray("sites").get(0).getAsJsonObject().addProperty("NoAI",false);no(()->authority(trait,plan(),proof()));
        JsonObject disabled=fixture();disabled.getAsJsonArray("sites").get(0).getAsJsonObject().add("species",strings("naturalist:dragonfly"));no(()->authority(disabled,plan(),proof()));
        JsonObject noProof=fixture();noProof.getAsJsonArray("sources").get(0).getAsJsonObject().addProperty("kind","FOREST_RECTANGLE");no(()->authority(noProof,plan(),proof()));
        no(()->new TownLifeAuthority(fixture(),"FIXTURE","FIXTURE","a".repeat(64),(r,c)->r.get("path").getAsString().contains("verify")?proof():plan(),r->{throw new IllegalStateException("Missing actual completion marker fixture");}));
        yes(()->{if(HabitatLifePolicy.SPECIES.values().stream().filter(HabitatLifePolicy.Species::enabled).count()!=15)throw new AssertionError();});
        System.out.println("PASS "+cases+" actual compiled town source-authority cases; fixtures are synthetic, no native scene/spawn/POI executed");
    }
}
