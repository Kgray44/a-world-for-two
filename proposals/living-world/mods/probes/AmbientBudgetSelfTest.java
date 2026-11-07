import worldfortwo.living.AmbientBudget;
import java.util.*;

/** Real JVM checks of pure admission state; no game, display, player or network is simulated. */
public final class AmbientBudgetSelfTest {
    private static void require(boolean value,String reason){if(!value)throw new AssertionError(reason);}
    private static UUID id(int value){return new UUID(0,value);}
    public static void main(String[] args){
        UUID alice=id(1),bob=id(2),a=id(11),b=id(12),c=id(13),d=id(14);
        AmbientBudget budget=new AmbientBudget();
        require(budget.admit(a,List.of(alice),0,20,3),"first Alice emission");
        require(!budget.admit(a,List.of(alice),0,20,3),"same speaker/tick does not repeat or charge");
        require(budget.emissions(alice,0)==1,"repeat charged once");
        require(budget.admit(b,List.of(alice),1,20,3),"second simultaneous Alice bubble");
        require(!budget.admit(c,List.of(alice,bob),2,20,3),"crowded shared audience refused atomically");
        require(budget.emissions(bob,2)==0,"refusal does not charge other observers");
        require(budget.admit(c,List.of(bob),2,20,3),"disjoint audience remains independent");
        require(budget.admit(d,List.of(alice,alice),20,20,3),"first active slot expires; duplicate audience charged once");
        require(budget.emissions(alice,20)==3,"Alice reaches three emissions");
        require(!budget.admit(id(15),List.of(alice),50,20,3),"active expiry does not reset minute rate");
        require(budget.admit(id(16),List.of(bob),50,20,3),"Alice minute cap does not silence Bob");
        require(budget.admit(id(17),List.of(alice),1200,20,3),"minute boundary expires oldest rate token");
        require(budget.emissions(alice,1200)==3,"only expired token was replaced");
        budget.clear();
        require(budget.admit(a,List.of(alice,bob),0,100,3),"shared observers accepted");
        require(budget.admit(b,List.of(alice,bob),1,100,3),"second shared bubble");
        budget.release(a,0);
        require(budget.simultaneous(alice,1)==1&&budget.simultaneous(bob,1)==1,"failed native add releases all observer slots");
        require(budget.emissions(alice,1)==2,"release does not refund admission rate");
        require(budget.admit(c,List.of(alice,bob),2,100,3),"released slot can be used");
        require(!budget.admit(d,List.of(alice,bob),3,100,3),"shared recipient rate limit enforced");
        require(!budget.admit(d,List.of(),4,100,3),"no observers means no display admission");
        require(!budget.admit(d,List.of(alice),4,1201,3),"unbounded native display lifetime refused");
        require(!budget.admit(d,List.of(alice),-1,100,3),"clock rollback cannot reset budget");
        budget.clear();
        require(budget.admit(a,List.of(alice),0,10,1),"lower configured limit accepted");
        require(!budget.admit(b,List.of(alice),20,10,1),"lower owner limit respected");
        System.out.println("AmbientBudget present-observer rate, simultaneous, expiry and refusal checks passed");
    }
}
