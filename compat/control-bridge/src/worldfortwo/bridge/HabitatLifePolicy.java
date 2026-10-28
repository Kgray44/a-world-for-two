package worldfortwo.bridge;

import java.util.*;

/** Isolated native44 proposal. Pure rules; source curation is not runtime acceptance. */
public final class HabitatLifePolicy {
    public enum Kind { DRY,AIR,SHORE,WATER,HOME,MUSIC }
    public enum Existing { NEW,PRESERVE }
    public record Artifact(String modId,String filename,long bytes,String sha256) {}
    public record Species(String nativeClass,String category,String artifact,String sourceClassSha256,Set<String> nativeResourceSha256,Kind kind,boolean enabled,int populationCap) {}
    public record Box(int minX,int minY,int minZ,int maxX,int maxY,int maxZ) {
        public long volume(){return ((long)maxX-minX+1)*(maxY-minY+1)*((long)maxZ-minZ+1);}
        public boolean contains(int x,int y,int z){return x>=minX&&x<=maxX&&y>=minY&&y<=maxY&&z>=minZ&&z<=maxZ;}
        public int width(){return maxX-minX+1;} public int height(){return maxY-minY+1;} public int depth(){return maxZ-minZ+1;}
    }
    public static final int WORLD_POPULATION_CAP=64,MAX_WITNESS_CELLS=4096;
    public static final String CURATION_SHA256="be41097fb361a62fb5b60cc93d33958a8a896048dbacdca72e6c87de8abe74d9";
    public static final String R5_COORDINATES_SHA256="e376a4e7c40fd51e26c7b983d05599d8e688bd27c3532d8c130bfdf4bdb41491";
    public static final List<Artifact> ARTIFACTS=List.of(
        new Artifact("naturalist","naturalist-2.0.7-neoforge-1.21.1.jar",11347884L,"2740593710eba0a917f862e535f3e2ef06c39ccdd6441986da02f9dd4394f03a"),
        new Artifact("crittersandcompanions","crittersandcompanions-neoforge-1.21.1-2.7.0.jar",2098079L,"bc09d4e9996fae2c17092b3f58e2cc6ffe49d176e7cdf06495eeb4ac9a85b5dd"),
        new Artifact("fishofthieves","fish_of_thieves-mc1.21.1-v21.1.3.0-neoforge.jar",1902440L,"d70f9c27b7eba24a58a04824faa0e64ac7c49eabf916c3bc2ebeab2d40dc85a8"),
        new Artifact("cozys_improved_cats","cozys-improved-cats-2.1.0-neoforge-1.21.1.jar",2154897L,"a459cf81b1a0f9f33e1e9d0c141b162c99c9c71cacc774cb04f139ed92df54c1"),
        new Artifact("doggytalents","DoggyTalentsNext-1.21.1-1.19.1.jar",11275139L,"38c8f223ecaca30297677ff828013ea27350b85517020c6bab2d16d71eb26ac0"),
        new Artifact("ribbits","Ribbits-1.21.1-NeoForge-4.1.6.jar",2215572L,"794223f5a91b8b80a962754b5180ec3e2472db6941e9b6c1cdd49324df628389"),
        new Artifact("fairytales","fairytales-neoforge-1211-1.0.0.jar",182486L,"dfafe8b18d488e7b0e72a28e07aef2a6f0986d4ec7fdfcd8642e4f614d86e6ac")
    );
    public static final Map<String,Species> SPECIES=Map.ofEntries(
        Map.entry("naturalist:deer",new Species("com.crispytwig.naturalist.world.entity.animal.deer.Deer","creature","naturalist","8e66970c359ac099b01b7dd303ec38ab10330fddaa6e32ec3b98fb15f310310a",Set.of("8e66970c359ac099b01b7dd303ec38ab10330fddaa6e32ec3b98fb15f310310a"),Kind.DRY,true,6)),
        Map.entry("naturalist:bird",new Species("com.crispytwig.naturalist.world.entity.animal.bird.Bird","creature","naturalist","b0246fddc99b0e8b4e41c93bf79e359e787ee8a3dea3602279c34408d5865be8",Set.of("b0246fddc99b0e8b4e41c93bf79e359e787ee8a3dea3602279c34408d5865be8"),Kind.AIR,true,6)),
        Map.entry("naturalist:butterfly",new Species("com.crispytwig.naturalist.world.entity.animal.butterfly.Butterfly","ambient","naturalist","ee7ee230ad1f2f9af10bcc69e8303ce5c5375e28f12cd15465b8f32d9a683c3b",Set.of("ee7ee230ad1f2f9af10bcc69e8303ce5c5375e28f12cd15465b8f32d9a683c3b"),Kind.AIR,true,8)),
        Map.entry("naturalist:firefly",new Species("com.crispytwig.naturalist.world.entity.animal.firefly.Firefly","ambient","naturalist","7bbaa15467bc649bb2bf3945406133a6b9e5e05631e73fbd85f665fc60a2208f",Set.of("7bbaa15467bc649bb2bf3945406133a6b9e5e05631e73fbd85f665fc60a2208f"),Kind.AIR,true,10)),
        Map.entry("naturalist:duck",new Species("com.crispytwig.naturalist.world.entity.animal.duck.Duck","creature","naturalist","8d2a6f37521fbf4079cec857cbb48c32db86e938dadd94239914fb5c2c9d211a",Set.of("8d2a6f37521fbf4079cec857cbb48c32db86e938dadd94239914fb5c2c9d211a"),Kind.SHORE,true,3)),
        Map.entry("naturalist:dragonfly",new Species("com.crispytwig.naturalist.world.entity.animal.dragonfly.Dragonfly","ambient","naturalist","668d6a9afd985471df3b08a6cf876c015ed8806a80f139dffdb4653f1f834a21",Set.of("668d6a9afd985471df3b08a6cf876c015ed8806a80f139dffdb4653f1f834a21"),Kind.AIR,false,2)),
        Map.entry("crittersandcompanions:shima_enaga",new Species("io.github.bonsaistudi0s.crittersandcompanions.common.entity.ShimaEnagaEntity","creature","crittersandcompanions","0f029b77f05cb73a8c201ede4c340cd4541e3788ed0d5f0d3022d38dac0cfa89",Set.of("0f029b77f05cb73a8c201ede4c340cd4541e3788ed0d5f0d3022d38dac0cfa89"),Kind.AIR,true,4)),
        Map.entry("crittersandcompanions:ladybug",new Species("io.github.bonsaistudi0s.crittersandcompanions.common.entity.LadybugEntity","ambient","crittersandcompanions","1368336196ff8ea7f67f74c014404826f2d4e755d0fe45b9294507319e92eb46",Set.of("1368336196ff8ea7f67f74c014404826f2d4e755d0fe45b9294507319e92eb46"),Kind.AIR,true,6)),
        Map.entry("crittersandcompanions:dragonfly",new Species("io.github.bonsaistudi0s.crittersandcompanions.common.entity.DragonflyEntity","ambient","crittersandcompanions","f4bf7d29556a2866061d30cbf1b7d553ddcd72627b7e43cd6cb2f6bbe5f702c5",Set.of("f4bf7d29556a2866061d30cbf1b7d553ddcd72627b7e43cd6cb2f6bbe5f702c5"),Kind.AIR,true,2)),
        Map.entry("crittersandcompanions:koi_fish",new Species("io.github.bonsaistudi0s.crittersandcompanions.common.entity.KoiFishEntity","water_ambient","crittersandcompanions","9757592f004a2dfd82c67ce0136ca9c3ca2f95372956857f064cdd1484fbcc13",Set.of("9757592f004a2dfd82c67ce0136ca9c3ca2f95372956857f064cdd1484fbcc13"),Kind.WATER,true,4)),
        Map.entry("fishofthieves:pondie",new Species("com.stevekung.fishofthieves.entity.animal.Pondie","water_ambient","fishofthieves","c3cd2d2c8fda603179f688881be1acb589315a14e322e7e025f461c9edb7f500",Set.of("c3cd2d2c8fda603179f688881be1acb589315a14e322e7e025f461c9edb7f500"),Kind.WATER,true,4)),
        Map.entry("cozys-improved-cats:improved_cat",new Species("net.cozy.cozysimprovedcats.entity.custom.ImprovedCatEntity","creature","cozys_improved_cats","033793508e250b9f2f972679d17031b7f1de8b0aaa3ec51d7bf30e4abd4058ac",Set.of("033793508e250b9f2f972679d17031b7f1de8b0aaa3ec51d7bf30e4abd4058ac"),Kind.DRY,true,2)),
        Map.entry("doggytalents:dog",new Species("doggytalents.common.entity.Dog","creature","doggytalents","9655bae174d72900ccedba990427c0026b1e9ea49b2e0e6ed0a45d30e08b0005",Set.of("9655bae174d72900ccedba990427c0026b1e9ea49b2e0e6ed0a45d30e08b0005"),Kind.DRY,true,1)),
        Map.entry("minecraft:villager",new Species("net.minecraft.world.entity.npc.Villager","misc","minecraft","e9f377dd09c67af5f25ad4e9e9eac74c6114e38e4e5e71ad368a8af318c1d70f",Set.of("670a30ec62cd1674690332fe766f02084ecee7f8fed1ce9a3d358d61283fb5c0","e9f377dd09c67af5f25ad4e9e9eac74c6114e38e4e5e71ad368a8af318c1d70f"),Kind.HOME,true,4)),
        Map.entry("ribbits:ribbit",new Species("com.yungnickyoung.minecraft.ribbits.entity.RibbitEntity","creature","ribbits","c3c0f8b7a61460f3d3586148ec55b85ae459cc71ad2077c2e6037a4d9eacadae",Set.of("c3c0f8b7a61460f3d3586148ec55b85ae459cc71ad2077c2e6037a4d9eacadae"),Kind.MUSIC,true,3)),
        Map.entry("minecraft:allay",new Species("net.minecraft.world.entity.animal.allay.Allay","creature","minecraft","9b018632ca6f13207854815384ae400c104cba3305821d698bbb845b6745da24",Set.of("7c07c32217df396c1d7e5030f3755c1c65b213bdd4faba61fdf0073474e35f81","9b018632ca6f13207854815384ae400c104cba3305821d698bbb845b6745da24"),Kind.AIR,true,1))
    );
    public static Species species(String id,String nativeClass,String category,String mode){
        Species p=SPECIES.get(id);
        if(p==null||!p.enabled||!p.nativeClass.equals(nativeClass)||!p.category.equals(category)||!p.kind.name().equals(mode))
            throw new IllegalStateException("Exact enabled species/class/category/habitat required: "+id);
        return p;
    }
    /** Legacy metadata query stays limited to its original four; it cannot upgrade v1 admission. */
    public static Species species(String id,String nativeClass,String category){
        if(!Set.of("naturalist:deer","naturalist:bird","naturalist:butterfly","naturalist:firefly").contains(id))throw new IllegalStateException("Legacy four-species query cannot admit extensions");
        Species p=SPECIES.get(id);return species(id,nativeClass,category,p.kind.name());
    }
    public static Existing existing(boolean priorIntent,boolean loaded,boolean exactIdentity){
        if(loaded){if(!priorIntent||!exactIdentity)throw new IllegalStateException("Preserve unowned or changed UUID; never adopt/replace blindly");return Existing.PRESERVE;}
        if(priorIntent)throw new IllegalStateException("Prior intent with unloaded/missing UUID remains uncertain; never duplicate");
        return Existing.NEW;
    }
    public static void live(boolean noAI,boolean passenger,boolean alive,boolean newborn,boolean tame,boolean owner){
        if(noAI||passenger||!alive||newborn&&(tame||owner))throw new IllegalStateException("Native AI/life/ownership flags refused");
    }
    public static void coordinate(double x,double y,double z){
        if(!Double.isFinite(x)||!Double.isFinite(y)||!Double.isFinite(z)||Math.floor(x)<912||Math.floor(x)>1352||Math.floor(z)< -1200||Math.floor(z)> -616||y<48||y>240)
            throw new IllegalStateException("Outside the finite observed south-bank study; rectangle is not habitat authority");
    }
    public static void known(Box b){
        if(b.minX>b.maxX||b.minY>b.maxY||b.minZ>b.maxZ||b.minX<904||b.maxX>1360||b.minZ< -1208||b.maxZ> -608||b.minY< -64||b.maxY>319||b.volume()<1||b.volume()>MAX_WITNESS_CELLS)
            throw new IllegalStateException("Complete bounded FULL habitat witness required");
    }
    public static void coordinateTown(double x,double y,double z){
        if(!Double.isFinite(x)||!Double.isFinite(y)||!Double.isFinite(z)||Math.abs(x)>30000000||Math.abs(z)>30000000||y<48||y>240)
            throw new IllegalStateException("Finite native town coordinate required; explicit authored authority still mandatory");
    }
    public static void knownTown(Box b){
        if(b.minX>b.maxX||b.minY>b.maxY||b.minZ>b.maxZ||Math.abs((long)b.minX)>30000000||Math.abs((long)b.maxX)>30000000
            ||Math.abs((long)b.minZ)>30000000||Math.abs((long)b.maxZ)>30000000||b.minY< -64||b.maxY>319||b.volume()<1||b.volume()>MAX_WITNESS_CELLS)
            throw new IllegalStateException("Complete finite native town FULL field required; a rectangle alone gives no admission");
    }
    public static void geometry(Species p,Box known,Box water,boolean hasBed,boolean hasJob,int routes){geometry(p,known,water,hasBed,hasJob,routes,false);}
    public static void geometry(Species p,Box known,Box water,boolean hasBed,boolean hasJob,int routes,boolean town){
        if(town)knownTown(known);else known(known);
        if(known.width()<5||known.depth()<5||known.height()<5)throw new IllegalStateException("A dry45-cell witness cannot admit these native44 habitats");
        if(p.kind==Kind.WATER||p.kind==Kind.SHORE){
            int span=p.kind==Kind.WATER?5:3;
            if(water==null||water.minX>water.maxX||water.minY>water.maxY||water.minZ>water.maxZ||water.width()<span||water.depth()<span||water.height()<2||water.volume()>847
                ||!known.contains(water.minX-1,water.minY,water.minZ-1)||!known.contains(water.maxX+1,water.maxY+1,water.maxZ+1))
                throw new IllegalStateException("Complete connected source-water plus surface/refuge witness required");
        }else if(water!=null)throw new IllegalStateException("Unexpected water authority for dry/air/home habitat");
        if(p.kind==Kind.HOME&&(!hasBed||!hasJob||routes!=2))throw new IllegalStateException("Actual distinct bed/job POIs and two complete routes required");
        if(p.kind==Kind.SHORE&&routes!=1||p.kind==Kind.MUSIC&&routes!=1)throw new IllegalStateException("Actual safe exit/music-home route required");
        if(p.kind!=Kind.HOME&&(hasBed||hasJob))throw new IllegalStateException("No fabricated POI assignment for an ordinary animal");
    }
    public static void budget(Map<String,Integer> counts){
        int total=0;for(var row:counts.entrySet()){Species p=SPECIES.get(row.getKey());int n=row.getValue();if(p==null||!p.enabled||n<0||n>p.populationCap)throw new IllegalStateException("Finite reviewed per-species population exceeded");total+=n;}
        if(total>WORLD_POPULATION_CAP)throw new IllegalStateException("Whole population exceeds64 including original wildlife");
    }
    private HabitatLifePolicy(){}
}
