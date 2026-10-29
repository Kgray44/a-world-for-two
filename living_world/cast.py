"""The ten configured roles and small habitat targets, not spawn authority.

Names, personalities, models and dialogue always come from the current registry.
Vanilla professions support authored roles; they do not implement bespoke jobs
such as guard combat, ship navigation or operating Create machines.
"""

ROLES = {
    'barnacle-bill': ('Tavern keeper', 'Tavern counter and private sleeping loft', 'minecraft:butcher', 'minecraft:smoker',
                      "The soup has passed inspection. The inspector has requested shore leave."),
    'old-finn': ('Fisherman', 'Waterfront fish shop and its upstairs bedroom', 'minecraft:fisherman', 'minecraft:barrel',
                 "That fish was enormous. The witnesses were smaller and less reliable."),
    'captain-blackthorn': ('Pirate captain', 'Harbor chart room and captain bedroom', 'minecraft:cartographer', 'minecraft:cartography_table',
                           "Navigation is simple: avoid the rocks, distrust the fog, count the spoons."),
    'mara-keel': ('Shipwright', 'Shipwright workshop and separate sleeping room', 'minecraft:toolsmith', 'minecraft:smithing_table',
                  "A ship is a carefully managed disagreement between wood and water."),
    'steward-pembroke': ('Royal steward', 'Castle accounts office and steward bedroom', 'minecraft:librarian', 'minecraft:lectern',
                         "The royal budget allows one small disaster. Please take a number."),
    'librarian-elm': ('Castle librarian', 'Castle library desk and librarian bedroom', 'minecraft:librarian', 'minecraft:lectern',
                      "Please whisper. The dramatic histories are already making a scene."),
    'captain-thimble': ('Royal guard captain', 'Castle gatehouse duty room and guard bedroom', 'minecraft:weaponsmith', 'minecraft:grindstone',
                        "The gate is secure. The goose remains a developing situation."),
    'poppy-green': ('Gardener', 'Homestead garden work area and household bedroom', 'minecraft:farmer', 'minecraft:composter',
                    "The weeds have formed a committee. I am declining their recommendations."),
    'foreman-rivet': ('Engineering foreman', 'Engineering workshop and staff bedroom', 'minecraft:toolsmith', 'minecraft:smithing_table',
                      "The machine is perfectly safe while everyone respects its personal space."),
    'mercy-tide': ('Harbor merchant', 'Harbor cargo ledger desk and merchant bedroom', 'minecraft:cartographer', 'minecraft:cartography_table',
                   "The price includes the cargo. Believing the sales pitch is complimentary."),
}

# TOTAL targets include existing residents and uncertain durable intents, never
# additional spawn counts. Only existing registered/curated species are used.
TARGETS = {
    'minecraft:villager': 16,  # ten named, then at most six ordinary residents
    'naturalist:deer': 4,
    'naturalist:bird': 4,
    'crittersandcompanions:shima_enaga': 2,
    'naturalist:butterfly': 4,
    'crittersandcompanions:ladybug': 4,
    'crittersandcompanions:dragonfly': 2,
    'crittersandcompanions:koi_fish': 4,
    'fishofthieves:pondie': 4,
    'naturalist:duck': 4,
    'naturalist:firefly': 6,
    'cozys-improved-cats:improved_cat': 2,
}

HABITATS = {
    'HOME': 'One real vanilla HOME bed head and compatible free job POI per villager, sheltered room, full body-clear routes to both; observe ordinary claims and sleep/work.',
    'DRY': 'Current safe footing, full body/headroom, roaming space and shelter; retain actual residents and player ownership.',
    'AIR': 'Current body-clear flight space and species-appropriate leaves, flowers or wetland support; fireflies need actual admitted darkness.',
    'WATER': 'Complete connected source water, minimum five by five and two deep plus proved surface/refuge; fresh native collision and swimming checks.',
    'SHORE': 'Connected source water at least three by three and two deep, plus a genuine gentle dry exit and full walkable shore route.',
}
