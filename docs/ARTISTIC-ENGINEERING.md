# Copper Wren mill quarter

The corrected R2 dry installation was placed and independently verified in the
separate artistic staging world on 27 October 2026. Its 7,710 target identities,
orientations, supplied block entities and inventories passed native verification.
This establishes installation, not functional commissioning or visual acceptance.
The actual screenshots exposed a floating roof ridge, plain glazing, a bland roof
and a dark, sparse operating room. A separate architectural R3 overlay is pending.
It must preserve the machines, water containment, controls, cargo and clear routes.

The quarter occupies dry land east of the palace, at x1303..1337,
z-1010..-936. The mill floor is Y67. It combines three contained Create waterwheels,
a millstone and press, filtered Overpressure flour delivery, a six-span powered
Hypertube route, and a 52-block station-to-station passenger shuttle. It does not
occupy the river or bridge clearance. Foundation admission reads an authenticated
stopped checkpoint; saved inventories, trees, water and supplied authored exclusions
are protected. Building materials satisfy the three/nine rule; all authored outdoor
surfaces are also checked against the nine-block maximum.

## Immutable installation identity

| Artifact | SHA-256 |
| --- | --- |
| R2 physical plan | `181e2191572846967c41e77bf5b406d0dddcc484488aa60d6725728ba651b199` |
| R2 manifest | `4339bb54a05d9c5a478b471db880c7d80dc1f6c0f25081824c7c54b75f49f408` |
| Original before-state plan | `042d7717761b938bd13150aae2d58483156cd5a243bd8950c7ade247d3ee775a` |

These original files remain unchanged. Private plans and receipts contain world
custody information and are retained outside Git. The original native before-state
proof is historical: its exact hash, completion marker, verification operation,
zero failures and truthful ordered timestamps are required, without an expiry.
It never substitutes for current-state verification.

After a new stopped checkpoint, a verification-only plan may replace **only** the
original payload's `backup_sha256` with the current verified checkpoint SHA.
Every other field, including geometry, palette, inventories and world identity,
must remain semantically identical. The explicit `native_after_plan` reference and
a fresh native after-proof are bound together. The after-proof must finish within
1,200 seconds before admission, cannot be future-dated and must follow the original
before-proof. The native helper also checks the actual current target blocks.
Applying R3 first invalidates this exact-R2 commissioning contract; use a separately
reviewed composite contract rather than masking differences.

## Executable commissioning proposal

`compat/control-bridge/proposals/ArtisticEngineeringSupport.java` is deliberately
outside the active bridge source tree until integration review. It uses the pinned
Create 6.0.10, Overpressure 0.1.7.4, Hypertube 0.6.0 and Railways 0.2.1 APIs.
Dedicated named-server compilation excludes the Minecraft client API. This is
compile evidence; first native execution remains pending.

The helper requires an empty-player window, an exclusive shared operation lease,
the exact running bridge/helper identity, current backup custody, exact artifact
and configuration hashes, and native FULL/block/entity readiness. It bounds its
own temporary simulation tickets and releases them and its lease on cancellation,
failure or server stop. It does not force-generate chunks. Immutable terminal
journals retain partial operations and cleanup failures.

The commissioning sequence performs these actual operations:

1. Recheck all dry R2 targets, orientations and empty processing inputs; initialize
   the pinned native kinetic components and railway graph.
2. Construct six native eight-block Bezier links. Each collision write must be
   admitted empty air with no block entity or intersecting entity. After the native
   setters, every filler cell must have the actual TubePath block entity, exact
   source owner and voxel volume produced by the pinned native normalizer.
3. Admit three contained water-source cells, require locked manual/sneak entry mode
   on both tube entrances, and release the directly adjacent wall-lever clutch.
4. Measure real RPM, stress and capacity; transfer the supplied 16 wheat and one
   iron ingot from the starter chest. Require actual dispatched flour, emptied
   input/transit inventories and one genuinely pressed iron sheet. No output goods
   or network speeds are fabricated.
5. Stop the real clutch, assemble only the admitted carriage through native Create
   station/glue APIs, and require one actual stationary, double-ended carriage with
   two bogeys and three native seats.

The main stop lever is at 1310,70,-999, directly south of its clutch. Hypertube
entrances are at 1331,71,-991 and 1331,71,-943. Their locked setting is manual/sneak
entry mode, not an emergency stop. The real drivetrain must be stopped for service.
The shuttle uses north/south station targets at 1336,69,-994 and 1336,69,-942.

Actual tube travel, passenger driving, two-player transport, fluid containment
under simulation and restart persistence remain unproved until native tests run.
The helper does not move passengers automatically. A partial failure preserves
real links, goods, glue and any assembled train; review the immutable receipt and
prepare explicit recovery rather than replaying commissioning blindly.

## Integration contract

The parent integration owns all versioning, builds, runtime installation and native
commands. Required hooks are:

```java
new ArtisticEngineeringSupport(candidate, bridge, interlock);
support.commands(registerCommandsEvent);
support.tick(server); // existing server tick owner
support.stop();       // before world save/close; also on owned cancellation
support.busy();       // include in all shared world-operation interlocks
```

`Interlock.acquire(owner, simulation)` must return the existing exclusive shared
lease, adapted to `Lease.valid()` and `Lease.close()`. No independent lock may let
this helper overlap settlement, bridge, craft or attraction operations. The helper
is console-only and requires permission level four.

Compilation needs the exact four pinned mod JARs plus Create's existing nested
Ponder 1.0.82 (including Catnip), Flywheel 1.0.6 and Registrate +67 on the compile
classpath. They are compile-only dependencies, never bundled into the bridge or
committed. Existing `NativeJournal`, `BridgePhaseGate` and `ChunkCacheAccess` sources
are reused unchanged.

After the parent creates a fresh zero-failure after-proof for the checkpoint-bound
verification-only plan, the evidence-only Python binder writes a new request:

```python
from tools.artistic_engineering import bind_commissioning
result = bind_commissioning(
    home, original_r2_bundle, exact_built_bridge_jar,
    candidate, bridge_version, original_native_before_receipt,
    fresh_native_after_receipt, checkpoint_bound_verification_plan,
)
```

This call does not launch, install, edit a world or invoke a command. The parent
then reviews the returned immutable request and may invoke `awftmill inspect` or
`awftmill commission` with its exact bundle name and SHA. `awftmill status` and
`awftmill cancel` expose progress and bounded cleanup.

Focused Python tests cover real mechanism connectivity and routes, collision and
glue bounds, protected saved contents, material rules, historical/current proof
roles, marker tampering, timestamps, ordering and the single-field checkpoint
rebind. Read-only peer review checked the pinned tube setter and station APIs and
identified the filler readback gap; that check is now explicit. Native acceptance
and R3 visual approval remain separate gates.
