package worldfortwo.tavern;

import java.lang.reflect.Method;
import java.util.*;
import net.minecraft.core.BlockPos;
import net.minecraft.util.profiling.InactiveProfiler;
import net.minecraft.util.profiling.ProfilerFiller;
import net.minecraft.world.entity.Mob;
import net.minecraft.world.level.pathfinder.*;

/** Actual native A* on a small synthetic floor; not a saved-world geometry test. */
public final class SurveyedPathScenarios {
    static void require(boolean condition,String message){if(!condition)throw new AssertionError(message);}
    static class Floor extends NodeEvaluator {
        final Set<BlockPos> admitted;final boolean constrained;
        Floor(Set<BlockPos> a,boolean c){admitted=a;constrained=c;}
        @Override public Node getStart(){return getNode(0,65,0);}
        @Override public Target getTarget(double x,double y,double z){return new Target(getNode((int)x,(int)y,(int)z));}
        @Override public PathType getPathTypeOfMob(PathfindingContext c,int x,int y,int z,Mob m){return PathType.WALKABLE;}
        @Override public PathType getPathType(PathfindingContext c,int x,int y,int z){return PathType.WALKABLE;}
        @Override public int getNeighbors(Node[] out,Node from){
            int count=0;
            for(int[] d:new int[][]{{1,0},{-1,0},{0,1},{0,-1}}){
                int x=from.x+d[0],z=from.z+d[1];if(x<0||x>4||z<0||z>2)continue;
                Node n=getNode(x,65,z);if(!n.closed)out[count++]=n;
            }
            return constrained?SurveyedPaths.keep(admitted,out,count,from):count;
        }
    }
    static Path search(Set<BlockPos> allowed,boolean constrained)throws Exception{
        Floor floor=new Floor(allowed,constrained);PathFinder finder=new PathFinder(floor,2048);
        // Invoke the exact native A* implementation without creating a world or
        // mob. Production uses its public findPath plus native WalkNodeEvaluator.
        Method method=PathFinder.class.getDeclaredMethod("findPath",ProfilerFiller.class,Node.class,Map.class,float.class,int.class,float.class);
        method.setAccessible(true);
        return (Path)method.invoke(finder,InactiveProfiler.INSTANCE,floor.getStart(),Map.of(floor.getTarget(4,65,0),new BlockPos(4,65,0)),32F,0,1F);
    }
    public static void main(String[] args)throws Exception{
        Set<BlockPos> allowed=new HashSet<>();for(int x=0;x<=4;x++)for(int z=0;z<=2;z++)allowed.add(new BlockPos(x,65,z));
        BlockPos furniture=new BlockPos(2,65,0);allowed.remove(furniture);
        Path old=search(allowed,false);require(old.canReach(),"old shortest route must reach");
        boolean crossed=false;for(int i=0;i<old.getNodeCount();i++)if(old.getNode(i).asBlockPos().equals(furniture))crossed=true;
        require(crossed,"old post-search veto would reject the furniture shortcut");
        Path fixed=search(allowed,true);require(fixed.canReach(),"native constrained A* must find the alternate aisle");
        for(int i=0;i<fixed.getNodeCount();i++)require(allowed.contains(fixed.getNode(i).asBlockPos()),"route must stay admitted");
        require(fixed.getNodeCount()>old.getNodeCount(),"alternate aisle is longer than rejected shortcut");
        Set<BlockPos> wall=new HashSet<>(allowed);wall.removeIf(p->p.getX()==2);Path blocked=search(wall,true);
        require(blocked==null||!blocked.canReach(),"a blocked room must remain unreachable");
        Node[] diagonal={new Node(1,65,1)};require(SurveyedPaths.keep(Set.of(new BlockPos(1,65,1)),diagonal,1,new Node(0,65,0))==0,"never cut a furniture corner diagonally");
        System.out.println("PASS:native A* finds admitted detour instead of rejected furniture shortcut; blocked aisle stays blocked; no diagonal corner cut. Synthetic floor only.");
    }
}
