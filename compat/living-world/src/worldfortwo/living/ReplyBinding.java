package worldfortwo.living;

import net.minecraft.server.MinecraftServer;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.server.level.ServerPlayer;
import net.minecraft.world.entity.npc.Villager;
import tn.naizo.smartvillagers.SmartVillagers;

/** Bound to one native delayed task and discarded with that task. */
public final class ReplyBinding {
    private final ServerPlayer player;
    private final Villager villager;
    private final DeliveryIdentity identity;
    private ReplyBinding(ServerPlayer player,Villager villager,boolean requireConsent){
        this.player=player;this.villager=villager;
        identity=new DeliveryIdentity(player,villager,WorldCharacters.current,requireConsent);
    }
    public static ReplyBinding capture(ServerPlayer player,Villager villager,boolean requireConsent){
        return new ReplyBinding(player,villager,requireConsent);
    }
    /** Must run on the server executor, immediately before the native delivery. */
    public boolean current(MinecraftServer server){
        if(server==null)return false;
        var livePlayer=server.getPlayerList().getPlayer(player.getUUID());
        var level=villager.level() instanceof ServerLevel serverLevel?serverLevel:null;
        var loaded=level==null?null:level.getEntity(villager.getUUID());
        var config=WorldCharacters.current;
        boolean consent=!identity.requireConsent()||SmartVillagers.conversations().privacy().hasConsent(player);
        return identity.permits(livePlayer,loaded,config,config.enabled(config.profile(villager.getUUID())),
            player.isAlive()&&!player.isRemoved()&&villager.isAlive()&&!villager.isRemoved(),
            player.level()==villager.level(),villager.distanceToSqr(player)<=256,consent);
    }
}
