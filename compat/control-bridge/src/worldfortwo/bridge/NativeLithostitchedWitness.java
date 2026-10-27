package worldfortwo.bridge;

import com.google.gson.*;
import com.mojang.serialization.*;
import dev.worldgen.lithostitched.api.registry.LithostitchedRegistries;
import dev.worldgen.lithostitched.api.worldgen.biomeinjector.BiomeInjector;
import dev.worldgen.lithostitched.api.worldgen.densityfunction.fastnoise.*;
import dev.worldgen.lithostitched.impl.LithostitchedInternalHooks;
import dev.worldgen.lithostitched.impl.worldgen.biomeinjector.internal.InjectorBiomeSource;
import dev.worldgen.lithostitched.impl.worldgen.biomeinjector.region.RegionManager;
import dev.worldgen.lithostitched.impl.worldgen.surface.rule.ReferenceRule;
import dev.worldgen.lithostitched.impl.worldgen.surface.rule.TransientMergedRule;
import java.io.*;
import java.lang.invoke.*;
import java.nio.charset.StandardCharsets;
import java.nio.file.*;
import java.security.*;
import java.time.Instant;
import java.util.*;
import net.minecraft.core.*;
import net.minecraft.core.registries.Registries;
import net.minecraft.resources.*;
import net.minecraft.world.level.Level;
import net.minecraft.world.level.biome.BiomeSource;
import net.minecraft.world.level.biome.Climate;
import net.minecraft.world.level.biome.MultiNoiseBiomeSource;
import net.minecraft.world.level.chunk.ChunkGenerator;
import net.minecraft.world.level.levelgen.*;
import net.neoforged.fml.ModList;

/** Original read-only EFFECTIVE-state evidence, not a replacement fingerprint.
 * Private output includes native seed state. Never log/upload it. Worker only.
 * Does not invoke a manager, bind(), load(), sample(), apply(), or generation.
 */
public final class NativeLithostitchedWitness {
    public static final long MAX_BYTES=16L*1024*1024,MAX_NANOS=60_000_000_000L;
    private static final long RESERVE=32_212_254_720L;
    private static final Gson JSON=new GsonBuilder().disableHtmlEscaping().create();
    private static final String[] ROUTERS={"barrier","fluid_level_floodedness","fluid_level_spread","lava","temperature","vegetation","continents","erosion","depth","ridges","initial_density_without_jaggedness","final_density","vein_toggle","vein_ridged","vein_gap"};
    private static final String LITHO_SHA="e0da669fa5facc61a09b9b7bae21b322993de1fcd1eb05787adffb7309598cca";
    private static final String CLIMATE_TREE="net.minecraft.world.level.biome.Climate$RTree";
    private static final Map<String,String> PINNED=Map.of(
        "impl/worldgen/surface/rule/TransientMergedRule","19b82e92c870cdd8d715293491322f2417a12004342eb1ccb9daeba0a99de97d",
        "impl/worldgen/surface/rule/ReferenceRule","12d3cd489545d889ab546280d3604a3efb042ab9a17708f6c79e6fdeec3c6db3",
        "impl/worldgen/biomeinjector/internal/InjectorBiomeSource","d2771e5954a7e14c5fee2ebd1a3bfbb87d33b7d10747ba096cbd57b6d53145b1",
        "impl/worldgen/biomeinjector/region/RegionManager","3a97a13164af130e0c8ae22a857bf2a73d7768df98b015129ad24a41b3adb928",
        "impl/worldgen/biomeinjector/region/RegionManager$BiomeRegions","ad7bedf69912b0d446a78c0d80d2d3b47aaaa6554aa060bb1ccea1caa546857c",
        "api/worldgen/densityfunction/fastnoise/FastNoiseConfig","b67f80f8fa5182939ad313f19258557747f79aff3020f30478b9023e1fcb6221",
        "api/worldgen/densityfunction/fastnoise/FNL","a851a84627adee3d392de266ee68a8c3ea0df71ff3c468f7fd528955d7acdc26");
    private final RegistryAccess access;private final RegistryOps<JsonElement> ops;
    private final long started=System.nanoTime();private int nodes,unknowns;private long bytes;
    private final OutputStream output;private final MessageDigest checksum=sha();
    NativeLithostitchedWitness(RegistryAccess access,OutputStream output){this.access=access;this.ops=RegistryOps.create(JsonOps.INSTANCE,access);this.output=output;}
    private void check(){if(System.nanoTime()-started>MAX_NANOS||++nodes>32768)throw new IllegalStateException("Finite witness traversal/deadline exceeded");}
    private void line(JsonObject value)throws IOException{check();byte[] raw=(JSON.toJson(value)+"\n").getBytes(StandardCharsets.UTF_8);if(raw.length>8*1024*1024||bytes+raw.length>MAX_BYTES-65536)throw new IOException("Finite private witness output exceeded");output.write(raw);checksum.update(raw);bytes+=raw.length;}
    private static JsonObject object(String type){var x=new JsonObject();x.addProperty("record",type);return x;}
    private JsonObject unknown(String reason){unknowns++;var x=object("UNKNOWN");x.addProperty("reason",reason);return x;}
    private <T>JsonElement encode(Codec<T> codec,T value){check();try{var result=codec.encodeStart(ops,value);if(result.result().isPresent())return result.result().get();return unknown("Native encoding unavailable: "+result.error().map(e->e.message()).orElse("no result"));}catch(RuntimeException|LinkageError e){return unknown("Native encoding threw "+e.getClass().getName());}}
    private static Object field(Object owner,Class<?> type,String name,Class<?> value)throws Throwable{return MethodHandles.privateLookupIn(type,MethodHandles.lookup()).findGetter(type,name,value).invoke(owner);}
    private static Object call(Object owner,String name,Class<?> result)throws Throwable{Class<?> type=owner.getClass();return MethodHandles.privateLookupIn(type,MethodHandles.lookup()).findVirtual(type,name,MethodType.methodType(result)).invoke(owner);}
    private static String key(Holder<?> holder){return holder.unwrapKey().map(k->k.location().toString()).orElse("DIRECT_HOLDER");}
    private JsonElement density(DensityFunction value,int depth)throws Throwable{
        check();if(depth>64)return unknown("Actual density holder nesting exceeded");
        if(value instanceof DensityFunctions.HolderHolder wrapper){var out=object("actual_density_holder_node");out.addProperty("class",value.getClass().getName());out.addProperty("holder",key(wrapper.function()));if(wrapper.function().unwrapKey().isPresent()){var current=access.registryOrThrow(Registries.DENSITY_FUNCTION).getHolder(wrapper.function().unwrapKey().get());if(current.isEmpty()||current.get()!=wrapper.function())out.add("holder_custody",unknown("Foreign density reference is not the actual current registry holder"));}out.add("current_held_value",density(wrapper.function().value(),depth+1));return out;}
        return encode(DensityFunction.DIRECT_CODEC,value);
    }

    /** Exact rule order is retained. original is diagnostic provenance, not the
     * effective rule list: the native merged CODEC encodes only original_source. */
    JsonObject surface(SurfaceRules.RuleSource rule,int depth,Set<Object> path)throws Throwable{
        check();if(depth>96||!path.add(rule))return unknown("Surface recursion/cycle bound");
        try{
            var out=object("surface_node");out.addProperty("class",rule.getClass().getName());
            if(rule instanceof TransientMergedRule merged){var list=new JsonArray();if(merged.rules().size()>4096)throw new IllegalStateException("Finite native merged rule count");for(var child:merged.rules())list.add(surface(child,depth+1,path));out.add("effective_rules_in_native_order",list);out.add("original_not_effective_fallback",surface(merged.original(),depth+1,path));}
            else if(rule instanceof ReferenceRule reference){var list=new JsonArray();if(reference.rules().size()>4096)throw new IllegalStateException("Finite surface holder count");for(var child:reference.rules()){var item=new JsonObject();item.addProperty("holder",key(child));item.add("current_value",surface(child.value(),depth+1,path));list.add(item);}out.add("current_referenced_rules_in_native_order",list);}
            else if(rule.getClass().getName().equals("net.minecraft.world.level.levelgen.SurfaceRules$SequenceRuleSource")){var list=new JsonArray();List<?> sequence=(List<?>)call(rule,"sequence",List.class);if(sequence.size()>4096)throw new IllegalStateException("Finite sequence count");for(Object child:sequence)list.add(surface((SurfaceRules.RuleSource)child,depth+1,path));out.add("sequence_in_native_order",list);}
            else if(rule.getClass().getName().equals("net.minecraft.world.level.levelgen.SurfaceRules$TestRuleSource")){out.add("condition",encode(SurfaceRules.ConditionSource.CODEC,(SurfaceRules.ConditionSource)call(rule,"ifTrue",SurfaceRules.ConditionSource.class)));out.add("then_run",surface((SurfaceRules.RuleSource)call(rule,"thenRun",SurfaceRules.RuleSource.class),depth+1,path));}
            else {out.add("native_leaf_encoding",encode(SurfaceRules.RuleSource.CODEC,rule));if(!Set.of("net.minecraft.world.level.levelgen.SurfaceRules$BlockRuleSource","net.minecraft.world.level.levelgen.SurfaceRules$Bandlands").contains(rule.getClass().getName()))out.add("effective_internal_state",unknown("Uninspected native/custom surface leaf internals; encoding alone is not full semantic proof"));}
            return out;
        }finally{path.remove(rule);}
    }

    JsonObject fastNoise(FastNoiseConfig config)throws Throwable{
        check();var out=object("fast_noise_native_state");out.addProperty("class",config.getClass().getName());out.addProperty("salt",config.salt());out.addProperty("frequency_bits",Integer.toHexString(Float.floatToRawIntBits(config.frequency())));out.add("native_config",encode(FastNoiseConfig.CODEC,config));
        FNL fnl=(FNL)field(config,FastNoiseConfig.class,"fnl",FNL.class);if(fnl==null)return unknown("Native FNL object absent");
        out.add("exact_fnl_fields_private_seed_included",fnlState(fnl));return out;
    }
    static JsonObject fnlState(FNL fnl)throws Throwable{
        var fields=new JsonObject();
        for(String name:List.of("mSeed","mOctaves"))fields.addProperty(name,(Integer)field(fnl,FNL.class,name,int.class));
        for(String name:List.of("mFrequency","mLacunarity","mGain","mWeightedStrength","mPingPongStrength","mFractalBounding","mCellularJitterModifier","mDomainWarpAmp"))fields.addProperty(name,Integer.toHexString(Float.floatToRawIntBits((Float)field(fnl,FNL.class,name,float.class))));
        for(String[] spec:new String[][]{{"mNoiseType","NoiseType"},{"mRotationType3D","RotationType3D"},{"mTransformType3D","TransformType3D"},{"mFractalType","FractalType"},{"mCellularDistanceFunction","CellularDistanceFunction"},{"mCellularReturnType","CellularReturnType"},{"mDomainWarpType","DomainWarpType"},{"mWarpTransformType3D","TransformType3D"}}){Class<?> type=Class.forName(FNL.class.getName()+"$"+spec[1],false,FNL.class.getClassLoader());Object value=field(fnl,FNL.class,spec[0],type);fields.addProperty(spec[0],value==null?"NULL":((Enum<?>)value).name());}
        return fields;
    }

    @SuppressWarnings("unchecked")
    JsonObject biome(BiomeSource source,int depth)throws Throwable{
        check();if(depth>16)return unknown("Biome delegate nesting exceeded");var out=object("biome_source");out.addProperty("class",source.getClass().getName());out.add("native_encoding",encode(BiomeSource.CODEC,source));
        if(source.getClass()==InjectorBiomeSource.class){var injected=(InjectorBiomeSource)source;out.add("direct_current_delegate",biome(injected.directDelegate(),depth+1));out.addProperty("root_is_direct_delegate",injected.rootDelegate()==injected.directDelegate());if(injected.rootDelegate()!=injected.directDelegate())out.add("root_current_delegate",biome(injected.rootDelegate(),depth+1));out.addProperty("base_resolver_class",injected.baseResolver==null?"NULL":injected.baseResolver.getClass().getName());if(injected.baseResolver!=injected.directDelegate())out.add("unexported_base_resolver",unknown("Actual base resolver is not the inspected direct delegate; no opaque resolver parity claim"));
            Map<?,?> grouped=(Map<?,?>)field(injected,InjectorBiomeSource.class,"injectorsByType",Map.class);if(grouped.size()>128)throw new IllegalStateException("Finite injector group count");var groups=new JsonArray();int group=0;
            for(var entry:grouped.entrySet()){var row=new JsonObject();row.addProperty("observed_group_index",group++);row.addProperty("codec_class",entry.getKey().getClass().getName());var list=new JsonArray();List<?> values=(List<?>)entry.getValue();if(values.size()>4096)throw new IllegalStateException("Finite applied injector count");for(Object value:values){BiomeInjector injector=(BiomeInjector)value;var item=new JsonObject();item.addProperty("class",injector.getClass().getName());item.addProperty("priority",injector.priority());item.addProperty("dimension",injector.dimension().location().toString());item.add("native_current_injector",encode(BiomeInjector.CODEC,injector));list.add(item);}row.add("applied_injectors_in_native_list_order",list);groups.add(row);}out.add("injector_groups_observed_map_order",groups);
            Object manager=field(injected,InjectorBiomeSource.class,"regionManager",RegionManager.class);out.add("current_region_manager",manager==null?JsonNull.INSTANCE:regions((RegionManager)manager));
            for(String name:List.of("possibleBiomes","replacedBiomes")){Object raw=field(injected,InjectorBiomeSource.class,name,List.class);if(raw==null){out.add(name,JsonNull.INSTANCE);continue;}List<?> values=(List<?>)raw;if(values.size()>32768)throw new IllegalStateException("Finite biome holder count");var ids=new JsonArray();for(Object value:values)ids.add(key((Holder<?>)value));out.add(name,ids);}
        }else if(source.getClass()==MultiNoiseBiomeSource.class){var parameters=(Climate.ParameterList<?>)call(source,"parameters",Climate.ParameterList.class);if(parameters.values().size()>16384)throw new IllegalStateException("Finite actual climate parameter count");var values=new JsonArray();for(var entry:parameters.values()){check();var row=new JsonObject();row.add("point",encode(Climate.ParameterPoint.CODEC,entry.getFirst()));row.addProperty("biome",key((Holder<?>)entry.getSecond()));values.add(row);}out.add("actual_current_parameter_values_in_native_order",values);Class<?> tree=Class.forName(CLIMATE_TREE,false,Climate.class.getClassLoader());Object index=field(parameters,Climate.ParameterList.class,"index",tree);Class<?> node=Class.forName(CLIMATE_TREE+"$Node",false,Climate.class.getClassLoader());out.add("actual_current_search_index",tree(field(index,tree,"root",node),node,0));out.addProperty("per_worker_last_result_hint_exported",false);
        }else if(!Set.of("net.minecraft.world.level.biome.FixedBiomeSource","net.minecraft.world.level.biome.CheckerboardColumnBiomeSource","net.minecraft.world.level.biome.TheEndBiomeSource").contains(source.getClass().getName()))out.add("unexported_custom_source_state",unknown("Custom non-injector biome source internals are not inspected"));
        return out;
    }
    private JsonObject tree(Object value,Class<?> node,int depth)throws Throwable{
        check();if(depth>48)return unknown("Native climate index nesting exceeded");var out=object("native_climate_index_node");out.addProperty("class",value.getClass().getName());var bounds=new JsonArray();for(Climate.Parameter parameter:(Climate.Parameter[])field(value,node,"parameterSpace",Climate.Parameter[].class)){var pair=new JsonArray();pair.add(parameter.min());pair.add(parameter.max());bounds.add(pair);}out.add("parameter_space_min_max",bounds);
        if(value.getClass().getName().equals(CLIMATE_TREE+"$SubTree")){Object[] children=(Object[])field(value,value.getClass(),"children",node.arrayType());if(children.length>16)throw new IllegalStateException("Finite native climate index children");var list=new JsonArray();for(Object child:children)list.add(tree(child,node,depth+1));out.add("children_in_native_order",list);}
        else if(value.getClass().getName().equals(CLIMATE_TREE+"$Leaf")){Object leaf=field(value,value.getClass(),"value",Object.class);if(leaf instanceof Holder<?> holder)out.addProperty("current_biome_holder",key(holder));else out.add("value",unknown("Native climate index leaf is not a biome holder"));}
        else out.add("state",unknown("Unrecognized native climate index node"));return out;
    }
    private JsonObject regions(RegionManager manager)throws Throwable{
        var out=object("effective_region_manager");Optional<?> function=(Optional<?>)field(manager,RegionManager.class,"regionFunction",Optional.class);out.add("current_region_function",function.isPresent()?density((DensityFunction)function.get(),0):JsonNull.INSTANCE);
        Map<?,?> map=(Map<?,?>)field(manager,RegionManager.class,"regionsByBiome",Map.class);if(map.size()>32768)throw new IllegalStateException("Finite biome-region count");var values=new JsonObject();for(var entry:map.entrySet()){Object value=entry.getValue();if(!value.getClass().getName().equals(RegionManager.class.getName()+"$BiomeRegions")){values.add(key((Holder<?>)entry.getKey()),unknown("Unknown native biome-region implementation"));continue;}var row=new JsonObject();row.addProperty("total_weight",(Integer)call(value,"totalWeight",int.class));TreeMap<?,?> outputs=(TreeMap<?,?>)call(value,"regionsByOutputs",TreeMap.class);if(outputs.size()>4096)throw new IllegalStateException("Finite region output map count");var array=new JsonArray();for(var region:outputs.entrySet()){var r=new JsonObject();r.addProperty("upper_output",(Integer)region.getKey());r.addProperty("region",((ResourceKey<?>)region.getValue()).location().toString());array.add(r);}row.add("ordered_output_regions",array);values.add(key((Holder<?>)entry.getKey()),row);}out.add("by_current_biome_holder",values);return out;
    }

    private void generator(ResourceKey<Level> dimension,ChunkGenerator chunk)throws Throwable{
        check();var out=object("actual_current_generator");out.addProperty("dimension",dimension.location().toString());out.addProperty("generator_class",chunk.getClass().getName());out.add("current_biome_source",biome(chunk.getBiomeSource(),0));
        if(chunk instanceof NoiseBasedChunkGenerator noise){Holder<NoiseGeneratorSettings> holder=noise.generatorSettings();var current=holder.unwrapKey().flatMap(key->access.registryOrThrow(Registries.NOISE_SETTINGS).getHolder(key));out.addProperty("settings_holder",key(holder));boolean exact=current.isPresent()&&current.get()==holder;out.addProperty("holder_is_actual_current_registry_reference",exact);if(!exact)out.add("holder_custody",unknown("Direct/foreign settings holder; no current reference parity claim"));NoiseGeneratorSettings settings=holder.value();out.add("effective_surface_tree",surface(settings.surfaceRule(),0,Collections.newSetFromMap(new IdentityHashMap<>())));
            NoiseRouter r=settings.noiseRouter();DensityFunction[] fields={r.barrierNoise(),r.fluidLevelFloodednessNoise(),r.fluidLevelSpreadNoise(),r.lavaNoise(),r.temperature(),r.vegetation(),r.continents(),r.erosion(),r.depth(),r.ridges(),r.initialDensityWithoutJaggedness(),r.finalDensity(),r.veinToggle(),r.veinRidged(),r.veinGap()};var routers=new JsonArray();for(int n=0;n<fields.length;n++){var value=new JsonObject();value.addProperty("index",n);value.addProperty("target",ROUTERS[n]);value.addProperty("class",fields[n].getClass().getName());value.add("native_current_encoding_or_explicit_holder_tree",density(fields[n],0));routers.add(value);}out.add("all_15_actual_router_fields_native_order",routers);
        }else out.add("non_noise_generator",unknown("Non-noise generator requires its own effective semantic witness"));line(out);
    }

    private record Identity(ChunkGenerator generator,BiomeSource biome,Holder<NoiseGeneratorSettings> holder,NoiseGeneratorSettings settings,NoiseRouter router){
        static Identity of(ChunkGenerator g){if(g instanceof NoiseBasedChunkGenerator n){var h=n.generatorSettings();var s=h.value();return new Identity(g,g.getBiomeSource(),h,s,s.noiseRouter());}return new Identity(g,g.getBiomeSource(),null,null,null);}
        boolean unchanged(){if(generator.getBiomeSource()!=biome)return false;if(holder==null)return true;var current=((NoiseBasedChunkGenerator)generator).generatorSettings();return current==holder&&current.value()==settings&&settings.noiseRouter()==router;}
    }

    /** Caller captures ACTUAL server level generators or current selected client
     * stems; never use the old @Shadow stem registry or reconstruct generators.
     * This method rejects main threads: dispatch on a separately owned worker.
     */
    public static Path write(RegistryAccess actual,Map<ResourceKey<Level>,ChunkGenerator> generators,Path privateDirectory,String id,String side)throws Throwable{
        if(Thread.currentThread().getName().equals("Server thread")||Thread.currentThread().getName().equals("Render thread"))throw new IllegalStateException("Read-only encoding must not run on the server/render tick thread");
        if(actual==null||generators==null||generators.isEmpty()||generators.size()>32||!Set.of("actual_server_levels","current_selected_client_stems").contains(side)||!id.matches("[a-z0-9][a-z0-9-]{0,63}"))throw new IllegalArgumentException("Actual current inputs, side and unique id required");
        generators=Map.copyOf(generators);var identities=generators.values().stream().map(Identity::of).toList();long nativeSeed=LithostitchedInternalHooks.WORLD_SEED;
        Path directory=privateDirectory.toAbsolutePath().normalize();if(!directory.startsWith(Path.of("D:/A World for Two"))||!Files.isDirectory(directory,LinkOption.NOFOLLOW_LINKS))throw new IOException("Existing private D output only");for(Path p=directory;p!=null;p=p.getParent())if(Files.isSymbolicLink(p))throw new IOException("Private output symlink refused");for(String drive:List.of("C:/","D:/"))if(Files.getFileStore(Path.of(drive)).getUsableSpace()<RESERVE+(drive.startsWith("D")?MAX_BYTES:0))throw new IOException("Host reserve unavailable");
        // Exact original resources must be verified against the unchanged pinned
        // archive; transformed class bytes are deliberately not reinterpreted.
        verifyPinnedArchive();verifyPinnedResources();verifyNativeHandles();Path data=directory.resolve(id+".lithostitched.jsonl"),status=directory.resolve(id+".lithostitched.status.json");if(Files.exists(status,LinkOption.NOFOLLOW_LINKS)||Files.exists(data,LinkOption.NOFOLLOW_LINKS))throw new IOException("Preserve previous witness/failure files");
        var terminal=object("witness_status");terminal.addProperty("at",Instant.now().toString());terminal.addProperty("side",side);terminal.addProperty("strict_parity_proved",false);boolean complete=false;
        try(OutputStream stream=Files.newOutputStream(data,StandardOpenOption.CREATE_NEW)){var witness=new NativeLithostitchedWitness(actual,stream);try{var header=object("private_effective_witness");header.addProperty("lithostitched_sha256",LITHO_SHA);header.addProperty("private_native_world_seed",nativeSeed);header.addProperty("not_a_fingerprint_or_acceptance_gate",true);witness.line(header);var sorted=new TreeMap<String,Map.Entry<ResourceKey<Level>,ChunkGenerator>>();for(var e:generators.entrySet())sorted.put(e.getKey().location().toString(),e);for(var e:sorted.values())witness.generator(e.getKey(),e.getValue());Registry<FastNoiseConfig> configs=actual.registryOrThrow(LithostitchedRegistries.FAST_NOISE_CONFIG);if(configs.size()>4096)throw new IllegalStateException("Finite FastNoise config count");var fnlStates=new IdentityHashMap<FastNoiseConfig,JsonElement>();for(var e:configs.entrySet()){var row=witness.fastNoise(e.getValue());fnlStates.put(e.getValue(),row.get("exact_fnl_fields_private_seed_included"));row.addProperty("current_registry_key",e.getKey().location().toString());witness.line(row);}if(LithostitchedInternalHooks.WORLD_SEED!=nativeSeed||identities.stream().anyMatch(i->!i.unchanged()))throw new IllegalStateException("Current native generator/holder/router/biome/global seed changed during export");for(var e:fnlStates.entrySet())if(!witness.fastNoise(e.getKey()).get("exact_fnl_fields_private_seed_included").equals(e.getValue()))throw new IllegalStateException("Native FNL state changed during export");witness.check();complete=true;}catch(Exception|LinkageError failure){terminal.addProperty("failure_class",failure.getClass().getName());terminal.addProperty("failure_message","Preserve private data; exact native API/codec/traversal failure, no fallback export");}finally{terminal.addProperty("complete_export",complete);terminal.addProperty("effective_state_coverage_complete",complete&&witness.unknowns==0);terminal.addProperty("unknown_effective_states",witness.unknowns);terminal.addProperty("observed_input_identities_unchanged",complete);terminal.addProperty("current_client_cache_stems_owner_recheck_required",side.equals("current_selected_client_stems"));terminal.addProperty("mutable_graphs_proven_immutable",false);terminal.addProperty("bytes",witness.bytes);terminal.addProperty("data_sha256",HexFormat.of().formatHex(witness.checksum.digest()));terminal.addProperty("elapsed_ms",(System.nanoTime()-witness.started)/1_000_000L);terminal.addProperty("acceptance","NOT PROVED: paired current-side comparison, generation provenance and native LOD/terrain remain required; UNKNOWN never equals proof");}}
        Files.writeString(status,JSON.toJson(terminal),StandardOpenOption.CREATE_NEW);return status;
    }
    private static MessageDigest sha(){try{return MessageDigest.getInstance("SHA-256");}catch(NoSuchAlgorithmException e){throw new AssertionError(e);}}
    private static void verifyPinnedArchive()throws Exception{
        var file=ModList.get().getModFileById("lithostitched");if(file==null)throw new IOException("Pinned native mod absent");Path path=file.getFile().getFilePath();
        if(Files.size(path)!=1023751L)throw new IOException("Pinned native archive size differs");try(InputStream input=Files.newInputStream(path)){byte[] bytes=input.readNBytes(1023752);if(bytes.length!=1023751||!HexFormat.of().formatHex(sha().digest(bytes)).equals(LITHO_SHA))throw new IOException("Pinned original native archive differs");}
    }
    static void verifyNativeHandles()throws Exception{
        var own=MethodHandles.lookup();var injector=MethodHandles.privateLookupIn(InjectorBiomeSource.class,own);
        injector.findGetter(InjectorBiomeSource.class,"injectorsByType",Map.class);injector.findGetter(InjectorBiomeSource.class,"regionManager",RegionManager.class);
        for(String field:List.of("possibleBiomes","replacedBiomes"))injector.findGetter(InjectorBiomeSource.class,field,List.class);
        var region=MethodHandles.privateLookupIn(RegionManager.class,own);region.findGetter(RegionManager.class,"regionFunction",Optional.class);region.findGetter(RegionManager.class,"regionsByBiome",Map.class);
        Class<?> values=Class.forName(RegionManager.class.getName()+"$BiomeRegions",false,RegionManager.class.getClassLoader());var inner=MethodHandles.privateLookupIn(values,own);inner.findVirtual(values,"regionsByOutputs",MethodType.methodType(TreeMap.class));inner.findVirtual(values,"totalWeight",MethodType.methodType(int.class));
        MethodHandles.privateLookupIn(FastNoiseConfig.class,own).findGetter(FastNoiseConfig.class,"fnl",FNL.class);
    }
    static void verifyPinnedResources()throws Exception{
        var loader=NativeLithostitchedWitness.class.getClassLoader();
        // Full archive identity is pinned by the installed recipe. Each required
        // original class resource is additionally checked by the offline fixture
        // and the integration must retain the existing full-archive admission.
        for(var pin:PINNED.entrySet())try(InputStream input=loader.getResourceAsStream("dev/worldgen/lithostitched/"+pin.getKey()+".class")){if(input==null)throw new IOException("Pinned native class unavailable");byte[] bytes=input.readNBytes(262145);if(bytes.length>262144||!HexFormat.of().formatHex(sha().digest(bytes)).equals(pin.getValue()))throw new IOException("Pinned native class identity differs");}
    }
}
