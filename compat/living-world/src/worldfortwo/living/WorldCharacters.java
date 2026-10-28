package worldfortwo.living;

import com.google.gson.*;
import java.util.*;
import java.util.concurrent.ThreadLocalRandom;

/** Immutable bounded configuration. No Minecraft, filesystem or network dependencies. */
public final class WorldCharacters {
    public static volatile WorldCharacters current = new WorldCharacters(new JsonObject());
    private final JsonObject document;
    private final Map<String, JsonObject> byEntity = new LinkedHashMap<>();
    private final Map<String, JsonObject> byId = new LinkedHashMap<>();
    private final Map<String, JsonObject> districts = new LinkedHashMap<>();
    private final Map<String, ArrayDeque<Long>> requests = new HashMap<>();
    private final Map<String, Long> last = new HashMap<>();
    private final Map<String, Long> ambientLast = new HashMap<>();
    private static final Map<Object, String> MEMORIES=Collections.synchronizedMap(new WeakHashMap<>());
    public WorldCharacters(JsonObject value) {
        document = value.deepCopy();
        if (array(value,"characters").size()>64 || array(value,"districts").size()>16)
            throw new IllegalArgumentException("Character allocation exceeded");
        for (JsonElement element : array(document,"characters")) {
            JsonObject profile=element.getAsJsonObject();
            if(byId.put(text(profile,"id"),profile)!=null)throw new IllegalArgumentException("Duplicate character identifier");
            String uuid=text(profile,"entity_uuid");
            if (!uuid.isEmpty()) {
                uuid=UUID.fromString(uuid).toString();
                if (byEntity.put(uuid,profile)!=null) throw new IllegalArgumentException("Duplicate entity UUID");
            }
        }
        for (JsonElement element:array(document,"districts")) {
            JsonObject district=element.getAsJsonObject();districts.put(text(district,"id"),district);
        }
    }
    public JsonObject profile(UUID entity) {return byEntity.get(entity.toString());}
    public JsonObject profileById(String id){return byId.get(id);}
    public JsonObject districtById(String id){return districts.get(id);}
    public Collection<String> entities(){return Collections.unmodifiableSet(byEntity.keySet());}
    public String revision(){return text(document,"revision");}
    public JsonObject settings(){return object(document,"settings");}
    public void memory(Object memory,UUID entity){MEMORIES.put(memory,entity.toString());}
    public static boolean memoryEnabled(Object memory){String entity=MEMORIES.get(memory);var config=current;var profile=config.byEntity.get(entity);return entity!=null&&config.enabled(profile)&&flag(object(profile,"ai"),"memory_enabled");}
    public static JsonObject object(JsonObject parent,String key){return parent!=null&&parent.has(key)&&parent.get(key).isJsonObject()?parent.getAsJsonObject(key):new JsonObject();}
    public static JsonArray array(JsonObject parent,String key){return parent!=null&&parent.has(key)&&parent.get(key).isJsonArray()?parent.getAsJsonArray(key):new JsonArray();}
    public static String text(JsonObject parent,String key){return parent!=null&&parent.has(key)&&!parent.get(key).isJsonNull()?parent.get(key).getAsString():"";}
    public static boolean flag(JsonObject parent,String key){return parent!=null&&parent.has(key)&&parent.get(key).isJsonPrimitive()&&parent.get(key).getAsJsonPrimitive().isBoolean()&&parent.get(key).getAsBoolean();}
    public static int integer(JsonObject parent,String key,int fallback){try{return parent.get(key).getAsInt();}catch(Exception ignored){return fallback;}}
    public static String limit(String value,int max){return value.length()>max?value.substring(0,max):value;}
    public boolean enabled(JsonObject profile){return profile!=null&&flag(profile,"enabled")&&text(profile,"kind").equals("villager");}
    public String district(UUID entity,String dimension,double x,double z){
        return district(entity,dimension,x,Double.NaN,z);
    }
    public String district(UUID entity,String dimension,double x,double y,double z){
        for(JsonObject district:districts.values()) {
            JsonObject b=object(district,"bounds");
            if(!text(b,"dimension").equals(dimension))continue;
            if(b.has("min_x")&&b.has("max_x")&&b.has("min_z")&&b.has("max_z")&&
                x>=b.get("min_x").getAsDouble()&&x<=b.get("max_x").getAsDouble()&&
                z>=b.get("min_z").getAsDouble()&&z<=b.get("max_z").getAsDouble()&&
                (!b.has("min_y")||!Double.isNaN(y)&&y>=b.get("min_y").getAsDouble())&&
                (!b.has("max_y")||!Double.isNaN(y)&&y<=b.get("max_y").getAsDouble()))return text(district,"id");
        }
        JsonObject p=profile(entity);return enabled(p)?text(p,"district"):"";
    }
    public List<String> lines(JsonObject profile,String category){
        List<String> result=new ArrayList<>();
        for(JsonElement e:array(object(object(profile,"dialogue"),"lines"),category))result.add(e.getAsString());
        if(result.isEmpty())for(JsonElement e:array(object(districts.get(text(profile,"district")),"dialogue"),category))result.add(e.getAsString());
        return result;
    }
    /** Profile markers take priority; district-only contexts use current shared lines. */
    public JsonObject ambientProfile(Set<String> states){
        for(String state:states)if(state.startsWith("awft_npc_")){
            JsonObject profile=profileById(state.substring(9));if(enabled(profile))return profile;
        }
        for(String state:states)if(state.startsWith("awft_district_")){
            String id=state.substring(14);if(districtById(id)!=null){JsonObject profile=new JsonObject();profile.addProperty("district",id);return profile;}
        }
        return null;
    }
    public record AmbientLine(String id,String text){}
    public List<AmbientLine> ambientLines(Set<String> states,String weather,String time,boolean reaction){
        JsonObject profile=ambientProfile(states);if(profile==null)return List.of();
        List<String> categories=new ArrayList<>();
        if(weather.equals("rain")||weather.equals("thunder"))categories.add("weather");
        if(time.equals("night"))categories.add("nighttime");
        if(reaction)categories.addAll(List.of("greetings","nearby_player","catchphrases"));
        else categories.addAll(List.of("contextual","greetings","tavern","starters","animals","nearby_player"));
        int humor=integer(object(profile,"dialogue"),"humor_intensity",5);
        if(humor>0)categories.add("jokes");
        String prefix="awft_dynamic_"+(text(profile,"id").isEmpty()?text(profile,"district"):text(profile,"id"));
        int max=Math.max(40,Math.min(240,integer(object(profile,"dialogue"),"max_response_chars",240)));
        List<AmbientLine> result=new ArrayList<>();
        for(String category:categories){int index=0;for(String line:lines(profile,category)){
            if(!line.isBlank())result.add(new AmbientLine(prefix+"_"+category+"_"+index,limit(line,max)));index++;
        }}
        return result;
    }
    public synchronized boolean ambientReady(UUID entity,long tick){
        JsonObject profile=profile(entity);if(profile==null)return true;if(!enabled(profile))return false;
        JsonObject dialogue=object(profile,"dialogue");
        long interval=Math.max(5,Math.max(integer(dialogue,"frequency_seconds",90),integer(dialogue,"cooldown_seconds",45)))*20L;
        Long previous=ambientLast.get(entity.toString());return previous==null||tick-previous>=interval;
    }
    public synchronized void ambientSent(UUID entity,long tick){if(profile(entity)!=null)ambientLast.put(entity.toString(),tick);}
    private static final Map<String,List<List<String>>> EXCHANGES=Map.of(
        "tortuga",List.of(
            List.of("Who put a treasure map on the tavern wall?","That's the bill. The cross marks what you owe."),
            List.of("Finn says the kraken borrowed his hat.","Then the kraken has finally made a poor decision."),
            List.of("The captain insists the ship is perfectly level.","Aye. Equally underwater at both ends."),
            List.of("KG calls that a harbor improvement.","Then why has the harbor asked for a second opinion?")),
        "rosewater",List.of(
            List.of("The royal spoon inspection begins at noon.","At last. The forks have grown insufferably smug."),
            List.of("I have filed the fairy's expense claim.","Under travel, or unexplained glitter?"),
            List.of("His Grace requests a less dramatic staircase.","I shall ask it to bow more quietly."),
            List.of("The librarian found a book that answers back.","A welcome improvement on the accounts department.")),
        "homestead",List.of(
            List.of("The hens have formed a committee.","Good. Perhaps they'll explain where the eggs are."),
            List.of("I planted a very orderly row of carrots.","The rabbits appreciate a well-arranged buffet."),
            List.of("There's a cat asleep on the recipe book.","Then supper will be whatever the cat recommends."),
            List.of("The garden looks particularly peaceful today.","The weeds are planning something. They always are.")),
        "engineering",List.of(
            List.of("I've solved the mysterious clicking noise.","Excellent. What's the new grinding noise?"),
            List.of("This machine requires only one small adjustment.","Is that the adjustment where we leave the building?"),
            List.of("KG says the train has tremendous potential.","Can we persuade some of it to become brakes?"),
            List.of("The contraption passed every test.","We should eventually write a second test.")));
    public boolean hasAmbientExchanges(){
        for(JsonObject district:districts.values()){
            if(EXCHANGES.containsKey(text(district,"id")))return true;
            JsonObject dialogue=object(district,"dialogue");
            if(!array(dialogue,"starters").isEmpty()&&!array(dialogue,"contextual").isEmpty())return true;
        }
        for(JsonObject profile:byEntity.values())if(enabled(profile)){
            JsonObject own=object(object(profile,"dialogue"),"lines");
            if(!array(own,"starters").isEmpty()&&!array(own,"contextual").isEmpty())return true;
        }
        return false;
    }
    public List<String> ambientExchange(Set<String> states){
        JsonObject profile=ambientProfile(states);if(profile==null)return List.of();
        JsonObject own=object(object(profile,"dialogue"),"lines");
        JsonArray starters=array(own,"starters"),replies=array(own,"contextual");
        // Authored personal call/response takes priority and changes with the saved registry.
        if(!starters.isEmpty()&&!replies.isEmpty())return List.of(
            limit(starters.get(ThreadLocalRandom.current().nextInt(starters.size())).getAsString(),240),
            limit(replies.get(ThreadLocalRandom.current().nextInt(replies.size())).getAsString(),240));
        List<List<String>> pool=EXCHANGES.get(text(profile,"district"));
        if(pool!=null)return pool.get(ThreadLocalRandom.current().nextInt(pool.size()));
        List<String> sharedStarters=lines(profile,"starters"),sharedReplies=lines(profile,"contextual");
        return sharedStarters.isEmpty()||sharedReplies.isEmpty()?List.of():List.of(
            limit(sharedStarters.get(ThreadLocalRandom.current().nextInt(sharedStarters.size())),240),
            limit(sharedReplies.get(ThreadLocalRandom.current().nextInt(sharedReplies.size())),240));
    }
    public String line(JsonObject profile,String category){
        List<String> pool=lines(profile,category);if(pool.isEmpty())pool=lines(profile,"greetings");
        return pool.isEmpty()?"I haven't a reliable answer for that. Ask me something local.":limit(pool.get(ThreadLocalRandom.current().nextInt(pool.size())),integer(object(profile,"dialogue"),"max_response_chars",280));
    }
    /** Current permission changes also govern old exchanges, not only new lore.
     * Any active secret omits all native history: an older reply may paraphrase a
     * revoked fact, so substring matching cannot reliably revoke that knowledge.
     * This is a conservative transmission policy, not a claim of semantic detection.
     */
    public boolean historyAllowed(JsonObject profile,String playerMessage,String villagerReply){
        if(!enabled(profile))return false;
        JsonObject knowledge=object(profile,"knowledge");
        List<JsonElement> entries=new ArrayList<>(array(knowledge,"entries").asList());
        if(flag(knowledge,"inherit_district"))entries.addAll(array(districts.get(text(profile,"district")),"entries").asList());
        for(JsonElement entry:entries)if(flag(entry.getAsJsonObject(),"secret"))return false;
        String exchange=(playerMessage+"\n"+villagerReply).toLowerCase(Locale.ROOT);
        for(JsonElement forbidden:array(knowledge,"forbidden_topics"))if(exchange.contains(forbidden.getAsString().toLowerCase(Locale.ROOT)))return false;
        JsonArray allowed=array(knowledge,"allowed_topics");
        if(!allowed.isEmpty()){
            for(JsonElement topic:allowed)if(exchange.contains(topic.getAsString().toLowerCase(Locale.ROOT)))return true;
            return false;
        }
        return true;
    }
    public String lore(JsonObject profile,String message){
        JsonObject knowledge=object(profile,"knowledge");
        String lower=message.toLowerCase(Locale.ROOT);
        for(JsonElement forbidden:array(knowledge,"forbidden_topics"))if(lower.contains(forbidden.getAsString().toLowerCase(Locale.ROOT)))return "That topic is private or outside this character's knowledge. Decline politely.";
        JsonArray allowed=array(knowledge,"allowed_topics");
        if(!allowed.isEmpty()){
            boolean matches=false;for(JsonElement topic:allowed)if(lower.contains(topic.getAsString().toLowerCase(Locale.ROOT)))matches=true;
            if(!matches)return "This subject is outside your allowed topics. Say you don't know; do not invent facts.";
        }
        List<JsonElement> entries=new ArrayList<>();
        entries.addAll(array(knowledge,"entries").asList());
        if(flag(knowledge,"inherit_district"))entries.addAll(array(districts.get(text(profile,"district")),"entries").asList());
        StringBuilder output=new StringBuilder();int count=0;
        for(JsonElement element:entries){
            JsonObject e=element.getAsJsonObject();String kind=text(e,"kind");
            if(flag(e,"secret")||!kind.equals("fact")&&!kind.equals("rumor")||kind.equals("rumor")&&!flag(knowledge,"allow_rumors"))continue;
            String entryScope=(text(e,"text")+" "+array(e,"topics")).toLowerCase(Locale.ROOT);
            boolean forbiddenEntry=false;
            for(JsonElement forbidden:array(knowledge,"forbidden_topics"))if(entryScope.contains(forbidden.getAsString().toLowerCase(Locale.ROOT)))forbiddenEntry=true;
            if(forbiddenEntry)continue;
            if(!allowed.isEmpty()){
                boolean permittedEntry=false;for(JsonElement topic:allowed)if(entryScope.contains(topic.getAsString().toLowerCase(Locale.ROOT)))permittedEntry=true;
                if(!permittedEntry)continue;
            }
            boolean match=array(e,"topics").isEmpty();
            for(JsonElement topic:array(e,"topics"))if(lower.contains(topic.getAsString().toLowerCase(Locale.ROOT)))match=true;
            if(!match)continue;
            if(kind.equals("fact")&&text(e,"source").isBlank())continue;
            String row="["+kind+"; "+text(e,"id")+"] "+limit(text(e,"text"),500)+"\n";
            if(output.length()+row.length()>2200||count>=6)break;output.append(row);count++;
        }
        return output.toString();
    }
    /** Charge admission, including failures; never retry or refund an attempted request. */
    public synchronized boolean admit(JsonObject profile,long now){
        JsonObject ai=object(profile,"ai"),settings=settings();
        if(!enabled(profile)||!flag(ai,"enabled")||!flag(settings,"external_enabled"))return false;
        String id=text(profile,"id");
        int cooldown=Math.max(5,integer(ai,"cooldown_seconds",20));
        if(now-last.getOrDefault(id,0L)<cooldown*1000L)return false;
        for(String key:List.of("*",id)){
            ArrayDeque<Long> queue=requests.computeIfAbsent(key,k->new ArrayDeque<>());
            while(!queue.isEmpty()&&now-queue.peekFirst()>=3600000L)queue.removeFirst();
            if(queue.size()>=Math.max(1,Math.min(60,integer(key.equals("*")?settings:ai,"requests_per_hour",12))))return false;
        }
        requests.get("*").addLast(now);requests.get(id).addLast(now);last.put(id,now);return true;
    }
}
