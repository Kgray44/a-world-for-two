import worldfortwo.living.DeliveryIdentity;

/** Deterministic source identity policy checks; no Minecraft objects or game boot. */
public final class DeliveryIdentitySelfTest {
    private static void check(boolean result,String message){if(!result)throw new AssertionError(message);}
    public static void main(String[] args){
        Object firstSession=new Object(),firstEntity=new Object(),configuration=new Object();
        var external=new DeliveryIdentity(firstSession,firstEntity,configuration,true);
        check(external.permits(firstSession,firstEntity,configuration,true,true,true,true,true),"Current same-session reply");
        check(!external.permits(new Object(),firstEntity,configuration,true,true,true,true,true),"Relogin may reuse UUID but cannot reuse session object");
        check(!external.permits(firstSession,new Object(),configuration,true,true,true,true,true),"Reloaded entity may reuse UUID but cannot reuse old object");
        check(!external.permits(firstSession,null,configuration,true,true,true,true,true),"Unloaded entity must drop reply");
        check(!external.permits(firstSession,firstEntity,new Object(),true,true,true,true,true),"Configuration reload must revoke a queued response");
        check(!external.permits(firstSession,firstEntity,configuration,false,true,true,true,true),"Disabled profile must drop reply");
        check(!external.permits(firstSession,firstEntity,configuration,true,false,true,true,true),"Dead participant must drop reply");
        check(!external.permits(firstSession,firstEntity,configuration,true,true,false,true,true),"Cross-dimension recipient must drop reply");
        check(!external.permits(firstSession,firstEntity,configuration,true,true,true,false,true),"Out-of-proximity recipient must drop reply");
        check(!external.permits(firstSession,firstEntity,configuration,true,true,true,true,false),"Revoked consent must drop external reply");
        var scripted=new DeliveryIdentity(firstSession,firstEntity,configuration,false);
        check(scripted.permits(firstSession,firstEntity,configuration,true,true,true,true,false),"No-consent scripted fallback remains usable");
        System.out.println("Delivery identity policy checks passed; no Minecraft or provider runtime started.");
    }
}
