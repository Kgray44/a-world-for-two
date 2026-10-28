package worldfortwo.bridge;

import com.google.gson.*;
import java.util.*;

/** Original read-only town site authority. It does not spawn, assign POIs, replay
 * plans/NBT, claim interiors from a forest rectangle or register a controller. */
public final class TownLifeAuthority {
    @FunctionalInterface public interface Reader {JsonObject read(JsonObject reference,int cap)throws Exception;}
    @FunctionalInterface public interface Completed {void check(JsonObject reference)throws Exception;}
    public record Cell(int x,int y,int z) {}
    public record Site(String id,Set<String> species,HabitatLifePolicy.Box known,Set<Cell> cells,Set<Cell> standing) {
        public void cell(int x,int y,int z){if(!cells.contains(new Cell(x,y,z)))throw new IllegalStateException("Native town body escaped explicitly reviewed authored occupancy cells");}
        public void standing(int x,int y,int z){if(!standing.contains(new Cell(x,y,z)))throw new IllegalStateException("Town footing/route was not explicitly reviewed");}
        public void member(String entity,HabitatLifePolicy.Box actual,double x,double y,double z){
            if(!species.contains(entity)||!known.equals(actual))throw new IllegalStateException("Town species/complete FULL known field differs from exact site authority");
            standing((int)Math.floor(x),(int)Math.floor(y),(int)Math.floor(z));
        }
    }
    private final Map<String,Site> sites;
    private static int integer(JsonElement value){try{if(!value.isJsonPrimitive()||!value.getAsJsonPrimitive().isNumber())throw new IllegalArgumentException();return value.getAsBigDecimal().intValueExact();}catch(Exception failure){throw new IllegalStateException("Literal integer town coordinate required",failure);}}
    private static Cell point(JsonElement value){JsonArray a=value.getAsJsonArray();if(a.size()!=3)throw new IllegalStateException("Three integer town coordinates required");Cell p=new Cell(integer(a.get(0)),integer(a.get(1)),integer(a.get(2)));if(Math.abs((long)p.x)>30000000||Math.abs((long)p.z)>30000000||p.y< -64||p.y>319)throw new IllegalStateException("Finite native town coordinate required");return p;}
    private static HabitatLifePolicy.Box box(JsonElement value){JsonArray a=value.getAsJsonArray();if(a.size()!=6)throw new IllegalStateException("Six exact town known bounds required");HabitatLifePolicy.Box b=new HabitatLifePolicy.Box(integer(a.get(0)),integer(a.get(1)),integer(a.get(2)),integer(a.get(3)),integer(a.get(4)),integer(a.get(5)));HabitatLifePolicy.knownTown(b);if(b.width()<5||b.height()<5||b.depth()<5)throw new IllegalStateException("Complete five-cell minimum town known field required");return b;}
    private static String text(JsonObject value,String key){return value.get(key).getAsString();}
    private static void identity(JsonObject value,String seed,String world){if(!text(value,"seed").equals(seed)||!text(value,"world_path").equals(world))throw new IllegalStateException("Authored town source belongs to another actual world");}
    public TownLifeAuthority(JsonObject document,String seed,String world,String checkpoint,Reader reader,Completed completed)throws Exception{
        if(!text(document,"format").equals("awft-town-life-authority:1")||!checkpoint.matches("[a-f0-9]{64}")||!text(document,"source_checkpoint_sha256").equals(checkpoint))throw new IllegalStateException("Exact typed authored town source checkpoint required");
        identity(document,seed,world);JsonArray sources=document.getAsJsonArray("sources"),entries=document.getAsJsonArray("sites");
        if(sources.isEmpty()||sources.size()>4||entries.isEmpty()||entries.size()>16)throw new IllegalStateException("Finite source-bound town batch required");
        Map<String,Set<Cell>> cellsBySource=new HashMap<>();int total=0;long bytes=0;
        for(JsonElement source:sources){
            JsonObject row=source.getAsJsonObject();if(!row.keySet().equals(Set.of("name","kind","plan","native_verify"))||!text(row,"kind").equals("AUTHORED_FULL_PLAN"))throw new IllegalStateException("Actual authored full geometry and native physical proof required");
            String name=text(row,"name");if(!name.matches("[a-z0-9][a-z0-9-]{0,63}")||cellsBySource.containsKey(name))throw new IllegalStateException("Distinct authored town source names required");
            JsonObject ref=row.getAsJsonObject("plan");bytes+=ref.get("bytes").getAsLong();if(bytes>16*1024*1024L)throw new IllegalStateException("Town source bytes exceed finite batch budget");
            JsonObject plan=reader.read(ref,8*1024*1024);identity(plan,seed,world);
            if(!text(plan,"format").equals("awft-native-settlement:1"))throw new IllegalStateException("A source reservation or guessed rectangle is not authored town geometry");
            JsonArray blocks=plan.getAsJsonArray("blocks"),palette=plan.getAsJsonArray("palette");
            if(blocks.isEmpty()||blocks.size()>250000||palette.isEmpty()||palette.size()>8192||total+blocks.size()>250000)throw new IllegalStateException("Finite full authored plan required");total+=blocks.size();
            JsonObject proofRef=row.getAsJsonObject("native_verify"),proof=reader.read(proofRef,512*1024);completed.check(proofRef);
            if(!text(proof,"operation").equals("verify")||!text(proof,"plan_sha256").equals(text(ref,"sha256"))||proof.get("blocks").getAsInt()!=blocks.size()
                ||proof.get("failures").getAsInt()!=0||proof.has("error")||!text(proof,"status").equals("verified actual block identities, orientation, block entities and supplied inventories")
                ||proof.has("cleanup_required")&&proof.get("cleanup_required").getAsBoolean()
                ||proof.has("temporary_tickets_remaining")&&proof.get("temporary_tickets_remaining").getAsInt()!=0
                ||proof.has("cleanup_passed")&&!proof.get("cleanup_passed").getAsBoolean())throw new IllegalStateException("Authored full plan lacks its actual exact native physical verification");
            Set<Cell> cells=new HashSet<>();
            for(JsonElement item:blocks){JsonArray a=item.getAsJsonArray();if(a.size()!=4)throw new IllegalStateException("Exact authored plan cells required");int state=integer(a.get(3));Cell p=point(new JsonArrayBuilder(a).point());if(state<0||state>=palette.size()||!cells.add(p))throw new IllegalStateException("Duplicate/invalid authored town cell");}
            cellsBySource.put(name,Set.copyOf(cells));
        }
        Map<String,Site> admitted=new LinkedHashMap<>();int occupancy=0;
        for(JsonElement item:entries){
            JsonObject row=item.getAsJsonObject();if(!row.keySet().equals(Set.of("id","source_names","species","known_bounds","occupancy_cells","standing_positions")))throw new IllegalStateException("No invented town trait/ownership/POI authority");
            String id=text(row,"id");if(!id.matches("[a-z0-9][a-z0-9-]{0,63}")||admitted.containsKey(id))throw new IllegalStateException("Distinct reviewed town site id required");
            HabitatLifePolicy.Box known=box(row.get("known_bounds"));Set<Cell> authored=new HashSet<>();Set<String> sourceNames=new HashSet<>();
            for(JsonElement name:row.getAsJsonArray("source_names")){String n=name.getAsString();if(!sourceNames.add(n)||!cellsBySource.containsKey(n))throw new IllegalStateException("Site must name actual authenticated authored sources");authored.addAll(cellsBySource.get(n));}
            if(sourceNames.isEmpty())throw new IllegalStateException("Town site lacks source authority");
            Set<Cell> cells=new HashSet<>(),standing=new HashSet<>();
            for(JsonElement value:row.getAsJsonArray("occupancy_cells")){Cell p=point(value);if(!known.contains(p.x,p.y,p.z)||!authored.contains(p)||!cells.add(p)||++occupancy>65536)throw new IllegalStateException("Town occupancy is not exact bounded authored geometry/AIR");}
            for(JsonElement value:row.getAsJsonArray("standing_positions")){Cell p=point(value);if(!cells.contains(p)||!authored.contains(new Cell(p.x,p.y-1,p.z))||!cells.contains(new Cell(p.x,p.y+1,p.z))||!standing.add(p)||standing.size()>64)throw new IllegalStateException("Reviewed town route needs authored floor, body and head cells");}
            if(cells.isEmpty()||standing.isEmpty())throw new IllegalStateException("Town body and standing mask cannot be empty");
            Set<String> species=new HashSet<>();for(JsonElement value:row.getAsJsonArray("species")){String key=value.getAsString();HabitatLifePolicy.Species p=HabitatLifePolicy.SPECIES.get(key);if(p==null||!p.enabled()||!species.add(key))throw new IllegalStateException("Town identity must remain in the same15-species curation");}
            if(species.isEmpty())throw new IllegalStateException("Explicit species per town site required");admitted.put(id,new Site(id,Set.copyOf(species),known,Set.copyOf(cells),Set.copyOf(standing)));
        }
        sites=Map.copyOf(admitted);
    }
    private record JsonArrayBuilder(JsonArray source){JsonArray point(){JsonArray point=new JsonArray();for(int i=0;i<3;i++)point.add(source.get(i));return point;}}
    public Site site(String id){Site site=sites.get(id);if(site==null)throw new IllegalStateException("No reviewed authored town site for this member");return site;}
}
