package net.antopfr.advancedweather.content.fluid;

// Derived from Advanced Weather 0.1.2, by Antopfr, under its MIT license.
// The fluid deliberately has no bucket. Explicitly supply AIR as its bucket
// instead of Registrate's default lookup for the unregistered mercury_bucket.
import com.tterrag.registrate.util.entry.FluidEntry;
import net.antopfr.advancedweather.AdvancedWeather;
import net.antopfr.advancedweather.util.AWRegistrate;
import net.minecraft.resources.ResourceLocation;
import net.minecraft.world.item.Items;
import net.neoforged.neoforge.fluids.BaseFlowingFluid;

public class AWFluids {
    public static final FluidEntry<BaseFlowingFluid.Flowing> MERCURY =
            AWRegistrate.get()
                    .fluid("mercury",
                            ResourceLocation.fromNamespaceAndPath(AdvancedWeather.MOD_ID, "block/mercury_still"),
                            ResourceLocation.fromNamespaceAndPath(AdvancedWeather.MOD_ID, "block/mercury_flow"))
                    .properties(p -> p.density(13500).viscosity(1500)
                            .canSwim(false).canDrown(false).canConvertToSource(false))
                    .fluidProperties(p -> p.bucket(() -> Items.AIR))
                    .noBlock()
                    .noBucket()
                    .register();

    public static void register() {}
}
