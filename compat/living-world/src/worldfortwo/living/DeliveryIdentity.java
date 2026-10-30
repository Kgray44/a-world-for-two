package worldfortwo.living;

/** One queued reply's original object identities, not a UUID-based session cache. */
public record DeliveryIdentity(Object player,Object villager,Object configuration,boolean requireConsent) {
    public boolean permits(Object livePlayer,Object loadedVillager,Object currentConfiguration,
                           boolean enabled,boolean alive,boolean sameDimension,boolean inRange,boolean consent){
        return player==livePlayer&&villager==loadedVillager&&configuration==currentConfiguration
            &&enabled&&alive&&sameDimension&&inRange&&(!requireConsent||consent);
    }
}
