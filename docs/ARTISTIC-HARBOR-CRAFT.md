# Sea Glass landing: real sailing craft

This source proposal adds **The Sea Glass Promise**, an actual Small Ships cog
entity at **1196.5, 63.1, −1264.5**, and a separate ordinary spruce tender at
**1194.5, 63.1, −1253.5**. Neither has been created or accepted by a player.
The furnished historic flagship remains architectural scenery; it is never
assembled into an enormous physics ship or represented as usable sailing craft.

The cog begins bow north, white sail furled, hull intact, shared and unlocked,
with its native configured cargo capacity empty. The tender rows west into open
water. There is no forged account ownership, invulnerability, loaded gun or
automatic chunk loader. UUID custody prevents a second copy when a player moves
or unloads either vessel.

The real pinned cog's stern envelope intersects precisely two plain deck cells
on the existing hammerhead: **1197,64,−1260** and **1198,64,−1260**. The plan
removes those two planks only. A nine-block east boarding apron connects around
the northern crane upright. The original crane, its ladder, lanterns, machinery,
workshop and inventories remain outside the permitted replacement set. A small
shore-spares barrel is initially empty. Native walking and hull boarding remain
explicit acceptance checks.

The tender has a separate short landing along X1196. A supported ladder outside
its body and westward launch envelope permits a return from water. The work is
small dock furniture rather than another waterfront building. Its timber joints
obey the 3/9 material rule, and the combined harbor must have no uninterrupted
material run beyond nine blocks, including outdoor decks.

## Native admission comes before creation

`tools/artistic_harbor_craft.py` writes a private wrapper, exact before-state
probe and water/air VERIFY probe. Its physical plan contains **no commands**.
Entity requests carry the actual native type, position, UUID and typed SNBT;
there is no generic `summon` shortcut. The parent owns native integration and
all world actions.

Immediately before each create or departure phase, the native server thread
must verify the exact bound water/air probe and query the complete real AABBs
after every target chunk is FULL and entity-ready. The six cog part envelopes,
passenger headroom, three-block cog water column and first eight northward
blocks are included. The tender uses the inspected vanilla dimensions
**1.375 × 0.5625 blocks**, additional clearance and eight westward departure
blocks. Coarse soundings only refuse obvious shallows; actual vegetation,
unexpected construction or a non-source water state must fail the native probe.

Every pet, other boat, dropped item and unlisted occupant blocks commissioning.
Only the exact commissioned cog and actual native multipart children may occupy
its subsequent departure query; the tender phase permits its own exact UUID.
Loaded **and persistent/unloaded** UUID custody is required independently of
spatial absence. All observations and the typed mutation must share the same
game tick, world binding and approved contract hash. Missing native integration
or missing authentic receipts leaves the request blocked. Fixture tests do not
satisfy those gates.

The exact cached Small Ships **2.0.2**, Create **6.0.10**, inspected native classes
and Minecraft boat dimensions are checked by the existing read-only pin audit.
NBT names and multipart dimensions derive from the pinned bytecode and the
[official Small Ships source revision](https://github.com/talhanation/smallships/tree/4bfb8680a3fecd8c7e71506b941a79c51c49dffb).
The tool executes no downloaded code and never authenticates an account.

## Acceptance still required

After native creation, inspect the actual loaded entity, complete multipart
body, furled sail, empty cargo and unchanged UUID. Walk to each boarding edge,
board both real craft and demonstrate controls, cargo, first departure, return
and controlled restart persistence. Demonstrate shared access with KG and Sera
before describing the craft as operational multiplayer content. Inspect real
shader screenshots of the vessel, pier connection and return ladder.

This landing does not commission a hoist. The harbor crane stays stopped until
its independent native assembly, controlled movement and empty-boat retention
checks pass. It must not be advertised as a functional boat lift from a visual
model or a passing pure geometry test.

Preparation accepts only an owner-bound isolated staging home, verified backup,
exact completed harbor plan and hash-bound actual shore profiles. An additional
fresh departure survey is required where the original shore profile ends before
the reserved launch corridor. Exports are unique, bounded to 8 MiB and immutable;
private world identity remains outside the repository.

## Narrow server integration

`compat/control-bridge/src/worldfortwo/bridge/HarborCraftSupport.java` exposes
`commands(RegisterCommandsEvent)`, `tick(MinecraftServer)`, `stopped()` and
`busy()`. Its constructor requires the pinned candidate version, bridge version
and an explicit shared world-operation interlock. Parent wiring and the next
bridge build are separate work. Stop cleanup must run before levels close.

The console-only root is:

```text
awftharborcraft inspect <artistic-harbor-craft-HASH16> <manifest-sha256>
awftharborcraft create  <artistic-harbor-craft-HASH16> <manifest-sha256>
awftharborcraft status
awftharborcraft cancel
```

Both operations require the isolated owner-bound artistic staging runtime and
an empty server. They validate the actual installed candidate, current verified
backup, exact document hashes and native Small Ships JAR/class pins. The native
factory supplies its real hull boxes and the vanilla boat's real dimensions.
Every physical landing target and body/departure cell is checked directly on
the server. Actual entity AABBs are queried without removing occupants.

UUID custody reads all active dimensions' entity region headers and queued
writes, then reads their entity NBT through the engine's own serialized
`SimpleRegionStorage` I/O. It never edits region files or instantiates stored
entities. Changes to header custody or new unscanned pending writes refuse the
operation. Loaded UUIDs, current readiness, source water, air and occupancy are
checked again immediately before creation on the same server tick.

The class ignores supplied SNBT. It constructs only two fixed safe native tags,
with no arbitrary type, position, passengers or inventory. Fsynced, exclusive
UUID reservation files precede the first native add. A partial add or unknown
outcome preserves the actual craft and blocks an automatic second creation.
Native initialization is observed for 30 ticks; real split parts, sail/hull
state, native cargo slots, position and velocity go into private receipts.
Nothing drives or teleports the boat, forges speed, deletes an entity or writes
a construction block.

Temporary tickets have a finite chunk/tick bound and are tracked before each
add. Cancellation, failure and stop release only those exact owned tickets.
Outstanding cleanup retains ownership and requires an explicit retry. Native
engine futures are shared work and are never cancelled. Immutable terminal
`NativeJournal` receipts remain authoritative; live gameplay acceptance stays
separate from creation and initialization.

The source compiled against the actual named Minecraft/NeoForge libraries.
A short standalone Minecraft NBT probe passed both fixed recipe round trips,
cross-language UUID5 identity and rejection of an unapproved entity type.
Those checks created no entity or world and do not prove the live integration.
