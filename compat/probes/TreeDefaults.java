import com.google.gson.Gson;

/** Prints this exact mod's public default config, without growing a tree. */
public class TreeDefaults {
    public static void main(String[] args) throws Exception {
        net.neoforged.fml.loading.FMLPaths.loadAbsolutePaths(java.nio.file.Path.of(args[0]));
        Object defaults = Class.forName("com.seasky.gianttree.Config.Config").getMethod("getDefaultConfig").invoke(null);
        System.out.println(new Gson().toJson(defaults));
    }
}
