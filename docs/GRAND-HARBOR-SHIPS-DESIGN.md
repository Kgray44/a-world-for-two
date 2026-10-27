# Grand Harbor: six original sailing ships

The four major ships are original architectural builds with curved, sealed wooden
hulls. They remain structural scenery that players can board and explore. No
giant hull is assembled into an Aeronautics/Sable physics object. Their smaller
tenders are genuine usable Minecraft boats. No downloaded schematic or film asset
is used.

| Vessel | Role and appearance | Hull | Sail state | Surveyed center | Deck floors |
| --- | --- | --- | --- | --- | --- |
| Rosewater Resolute | Prestigious blue flagship, three masts, glazed stern gallery, officer accommodation, tender davits | 79 × 23 | Partially unfurled drying canvas | 1140, -1450 | 57, 61, 65, 69 |
| Amberwake | Broad yellow merchantman, three masts, more cargo and fewer guns | 63 × 21 | Tightly furled | 1000, -1350 | 58, 62, 66, 70 |
| Nightingale's Debt | Lean red corsair, two masts, denser berths and broadside battery | 57 × 17 | Tightly furled | 1110, -1344 | 58, 62, 66, 70 |
| Sea Lavender | Cyan coastal dispatch escort, two masts and lighter battery | 49 × 17 | Fully loosened, hanging and gently billowed drying canvas | 1230, -1376 | 59, 63, 67, 71 |

Dimensions are Minecraft blocks. The four original hulls vary in length, beam,
rig, cargo treatment, crew density, colour, battery and cabin proportions. The
design follows the organizational references in
[Ship design references](SHIP-DESIGN-REFERENCES.md), rather than reproducing a
particular museum ship. Sea level comes from the actual native water-block survey
at Y63; the keel drafts are respectively eight, seven, seven and six blocks.

The first dock positions failed conservative depth checks. The final positions
above move into surveyed deep water. The generator checks the upper envelope of
four surrounding ocean-floor soundings for each sampled submerged hull position.
It refuses shallow locations and incomplete surveys; it never excavates the
seabed to make a ship fit. A coarse sounding is still not proof of every natural
block beneath a hull.

Each large ship contains eleven named experiences: the safe magazine, cargo and
ballast hold, food/water stores, forward galley, crew hammocks, mess, officer
berths/wardroom, broadside gun deck, navigation office, captain's stern cabin and
open weather deck. Two continuous ladder trunks connect four distinct decks;
paired stairs reach raised quarterdecks and forecastles. Central and branching
passages have explicit two-block headroom. A graph check establishes that each
named room anchor reaches the shared landing in the generated geometry. Native
collision shapes and real walking remain a separate check.

The captain's spaces have a real bed, writing desk, chart table, model ship,
storage and seating. The crew deck uses two-part Comforts hammocks with end posts,
personal lockers, tables and a cold galley range. The lower hold has role-specific
cargo, maintenance, sail and rope stores. A bulkhead separates the magazine from
food and galley areas. It contains empty decorative barrels, with its lantern
outside. There is no TNT, live powder, projectile, loaded cannon, firing circuit
or automatic combat. The 14/8/10/6 broadside guns use unloaded Create Big Cannons
barrel/chamber/end blocks on original timber trucks; they are not assembled firing
contraptions.

The hull's stepped bilges are sealed on every face. Merely outlining the sides
would leave holes beneath widening sections, so the generator also seals lower
and longitudinal boundary faces. A separate preflight rejects any planned
underwater air cell with an unplanned neighbour. This is design evidence; the
placed world still needs a wet-hull inspection.

Three-wide stair gangways lead down from the docked ships to five-wide, timber
finger piers. The piers join a common promenade at Z -1247, then meet the existing
Lanternwater boardwalk at 1150,65,-1241. The promenade yields to every recorded
completed core/port/bridge block, including air clearance and inventory positions.
Its crossing of the original lower pier preserves that pier and provides a small
stair transition. Original mooring bollards, cargo pockets and sparse lanterns
give the quays purpose without filling the ocean with stone.

The offshore flagship has a water-level boarding ladder, two usable tender boats,
two original davit arms and an isolated native Create hand crank, shaft and rope
pulley over a small cradle. Cradle glue, actual vertical movement, safe boat
retention and restart persistence require commissioning. The geometry does not
claim that a boat has been attached to the pulley or that a static davit is a
working lift. The entire flagship must never be glued to this small mechanism.
The inner hull railing is explicitly opened at the ladder landing. Separate
marked mooring buoys connect to preserved ship rails with visible lines, continuous
ground chains and seabed anchor shapes; the shipboard anchors remain stowed near
the hull. These are structural moorings with no continuous giant-ship simulation.

The independent access plan adds the furnished Copper Minnow fishing cutter and
Silver Kestrel fishing/supply craft, with little cabins, a cockpit, tackle, stores
and furled working sails. Three usable boats wait at the tender landing; a fourth
usable chest boat sits in the surveyed open river channel. Together with the two
offshore tenders these are six small interactive service boats, separate from the
two small structural sailing ships. Entity UUIDs are deterministic so native
construction can avoid duplicating an already loaded named tender.

`python -m tools.settlement_ships` prepares only the four vessel-specific immutable
plans and manifests. `python -m tools.settlement_ships --access` separately prepares
the shared quay after those four plans exist. Neither command contacts the server,
changes the current `plan.json`, or places blocks. The parent deployment workflow
owns the complete backup, native admission/placement/verification and receipts.

The latest native marine survey, actual block registry, exact completed master
plans and all known earlier block-entity exclusions are inputs. Every requested
state property must exist in the native registry; unknown properties fail closed.
Plans and manifests stay private with the world. Only this original generator and
the design/verification description belong in Git.

Acceptance still requires native block and inventory verification, dry hulls,
headroom and ladder checks, real gangway walking, usable tender boarding, working
isolated hoist, restart persistence, measured harbor performance and actual
intended-shader screenshots of exteriors and interiors. The flagship, dockside
rig silhouettes and pirate quarter should then be framed in the actual first-join
cinematic. Generated plans and synthetic tests do not establish visual quality or
complete the addenda by themselves.
