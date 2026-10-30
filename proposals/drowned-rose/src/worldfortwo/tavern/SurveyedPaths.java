package worldfortwo.tavern;

import java.util.Set;
import net.minecraft.core.BlockPos;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.world.entity.Mob;
import net.minecraft.world.level.PathNavigationRegion;
import net.minecraft.world.level.pathfinder.Node;
import net.minecraft.world.level.pathfinder.Path;
import net.minecraft.world.level.pathfinder.PathFinder;
import net.minecraft.world.level.pathfinder.WalkNodeEvaluator;

/** Native A* with the finite survey applied while expanding, before route selection. */
final class SurveyedPaths {
    private final PathFinder finder;

    SurveyedPaths(Set<BlockPos> admitted) {
        WalkNodeEvaluator evaluator=new WalkNodeEvaluator(){
            @Override public int getNeighbors(Node[] options,Node from){
                return keep(admitted,options,super.getNeighbors(options,from),from);
            }
        };
        evaluator.setCanPassDoors(true);
        evaluator.setCanOpenDoors(false);
        evaluator.setCanFloat(false);
        finder=new PathFinder(evaluator,2048);
    }

    static int keep(Set<BlockPos> admitted,Node[] options,int count,Node from){
        int kept=0;
        for(int i=0;i<count;i++){
            Node candidate=options[i];
            // Native collision, floor height, headroom and jump rules ran
            // first. Exclude furniture before A* chooses its shortcut. Cardinal
            // routes also avoid cutting across an excluded furniture corner.
            if(!admitted.contains(candidate.asBlockPos())||
                Math.abs(candidate.x-from.x)+Math.abs(candidate.z-from.z)!=1)continue;
            options[kept++]=candidate;
        }
        return kept;
    }

    Path create(ServerLevel level,Mob mob,BlockPos target){
        // Exactly the already-admitted four chunks; caller verifies all loaded.
        // No chunk ticket, geometry edits, synthetic path or replacement mob.
        PathNavigationRegion region=new PathNavigationRegion(level,
            new BlockPos(1293,63,-1288),new BlockPos(1310,72,-1271));
        return finder.findPath(region,mob,Set.of(target),32F,0,1F);
    }
}
