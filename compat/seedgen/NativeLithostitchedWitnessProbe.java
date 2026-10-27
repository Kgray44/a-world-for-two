package worldfortwo.bridge;

import com.google.gson.*;
import dev.worldgen.lithostitched.api.worldgen.densityfunction.fastnoise.FNL;
import dev.worldgen.lithostitched.impl.worldgen.surface.rule.TransientMergedRule;
import java.io.ByteArrayOutputStream;
import java.util.*;
import net.minecraft.SharedConstants;
import net.minecraft.core.RegistryAccess;
import net.minecraft.server.Bootstrap;
import net.minecraft.world.level.block.Blocks;
import net.minecraft.world.level.levelgen.SurfaceRules;
import net.minecraft.world.level.biome.*;
import net.minecraft.core.Holder;
import com.mojang.datafixers.util.Pair;

/** Synthetic original objects only; never connects a client or loads a world. */
public final class NativeLithostitchedWitnessProbe {
    public static void main(String[] args)throws Throwable{
        SharedConstants.tryDetectVersion();Bootstrap.bootStrap();
        NativeLithostitchedWitness.verifyPinnedResources();
        NativeLithostitchedWitness.verifyNativeHandles();
        var witness=new NativeLithostitchedWitness(RegistryAccess.EMPTY,new ByteArrayOutputStream());
        var original=SurfaceRules.state(Blocks.STONE.defaultBlockState());
        var a=new TransientMergedRule(List.of(SurfaceRules.state(Blocks.DIRT.defaultBlockState())),original);
        var b=new TransientMergedRule(List.of(SurfaceRules.state(Blocks.GRAVEL.defaultBlockState())),original);
        var first=witness.surface(a,0,Collections.newSetFromMap(new IdentityHashMap<>()));
        var second=witness.surface(b,0,Collections.newSetFromMap(new IdentityHashMap<>()));
        if(first.get("effective_rules_in_native_order").equals(second.get("effective_rules_in_native_order")))throw new AssertionError("Effective merged surface difference hidden");
        if(!first.get("original_not_effective_fallback").equals(second.get("original_not_effective_fallback")))throw new AssertionError("Unchanged original surface changed");
        var nested=SurfaceRules.sequence(SurfaceRules.ifTrue(SurfaceRules.ON_FLOOR,a),b);
        var tree=witness.surface(nested,0,Collections.newSetFromMap(new IdentityHashMap<>()));
        if(!tree.toString().contains("then_run")||!tree.toString().contains("sequence_in_native_order"))throw new AssertionError("Native nested test/sequence getters not resolved");
        var effects=new BiomeSpecialEffects.Builder().fogColor(0).waterColor(0).waterFogColor(0).skyColor(0).build();
        var biome=Holder.direct(new Biome.BiomeBuilder().hasPrecipitation(true).temperature(.5f).downfall(.5f).specialEffects(effects).mobSpawnSettings(MobSpawnSettings.EMPTY).generationSettings(BiomeGenerationSettings.EMPTY).build());
        var zero=new Climate.Parameter(0,0);var point=new Climate.ParameterPoint(zero,zero,zero,zero,zero,zero,0);
        var climate=new Climate.ParameterList<>(List.of(Pair.of(point,biome),Pair.of(new Climate.ParameterPoint(new Climate.Parameter(2,3),zero,zero,zero,zero,zero,0),biome)));
        var observed=witness.biome(MultiNoiseBiomeSource.createFromList(climate),0);
        if(!observed.toString().contains("children_in_native_order")||!observed.toString().contains("current_biome_holder")||observed.getAsJsonArray("actual_current_parameter_values_in_native_order").size()!=2)throw new AssertionError("Actual climate parameter list/index private getters failed");
        var fnl=new FNL(12345);var left=NativeLithostitchedWitness.fnlState(fnl);fnl.SetSeed(543210);var right=NativeLithostitchedWitness.fnlState(fnl);
        if(left.size()!=18||right.size()!=18||left.get("mSeed").equals(right.get("mSeed")))throw new AssertionError("Actual FNL seed/schema not read");
        System.out.println("PASS exact7 original class guards; actual pinned API nested effective merged/sequence/test rules differ while original matches; all18 exact FNL fields read and synthetic SetSeed difference observed");
        System.out.println("NOT RUN native FastNoiseConfig construction/bind (requires actual Apollib config lifecycle), server/client generator capture, applied injector/region data, transformed classloader, paired parity or terrain/LOD acceptance");
    }
}
