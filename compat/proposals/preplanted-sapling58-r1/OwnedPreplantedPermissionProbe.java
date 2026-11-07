package worldfortwo.bridge;
public final class OwnedPreplantedPermissionProbe {
 static int checks;static void check(boolean v){checks++;if(!v)throw new AssertionError("owned-root boundary "+checks);}
 public static void main(String[]a){
  boolean[] bits={true,true,true,true,false,false,false,true,false,false};
  check(TreeGrowthScope.ownedPreplantedPermission(true,true,true,true,false,false,false,true,false,false));
  for(int i=0;i<bits.length;i++){boolean[] x=bits.clone();x[i]=!x[i];check(!TreeGrowthScope.ownedPreplantedPermission(x[0],x[1],x[2],x[3],x[4],x[5],x[6],x[7],x[8],x[9]));}
  check(!TreeGrowthScope.ownedPreplantedPermission(false,true,true,true,false,false,false,true,false,false));
  check(!TreeGrowthScope.ownedPreplantedPermission(true,false,true,true,false,false,false,true,false,false));
  check(!TreeGrowthScope.foliageOverlap(true,true,true,false,false,true,false,false,false));
  check(!TreeGrowthScope.naturalCanopyOverlap(true,true,true,true,false,false,false,true,false,false));
  System.out.println("{\"permission_checks\":"+checks+",\"passed\":true,\"world_started\":false}");
 }
}
