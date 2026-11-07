# Pending0.1.11: surveyed native chair exit

This source is now combined with the precisely scoped Smooth NPC pose correction
in the0.1.11 review candidate; see SMOOTH-POSE-0111.md. It has not been installed.
The installed0.1.10 JAR and normal-stop5f7983 saved396 checkpoint are retained.
Compilation and simulated checks do not establish actual safe chair exits.

## Actual failure and scope

At07:05:56UTC six patrons shared1299.5,65,-1277.5, outside the surveyed graph
and two cardinal steps from admitted transit.349 of1,480 path requests had
returned native_incomplete. Handcrafted's fallback dismount can select a seat
center when adjacent positions fail. That is a plausible origin of the stack;
the actual transition that put these six there was not observed.

This change prevents the adapter's future chair exits from using that fallback.
It does not move or repair those six already-stuck patrons. The ordinary path
graph, native A*, furniture geometry and body collision rules are unchanged.

## Change

* Resolve the reviewed chair from the actual managed vehicle's block position.
  Require its surveyed block state, admitted approach, existing four loaded
  chunks, containment boundary and unchanged destination reservations.
* Require the seat's saved resident UUID to match its actual passenger. Ask
  native DismountHelper.findSafeDismountLocation for that approach, preserving
  Handcrafted's0.25-block exit lift. Check the real passenger's moved bounding
  box and nearby living bodies, including players. Do not load chunks.
* If blocked, retain the mount, arrival state and old destination reservation;
  retry through the ordinary scheduler. Do not commit a new activity/history.
* If clear, call native LivingEntity.stopRiding once. The owned seat's
  getDismountLocationForPassenger supplies the reviewed point only during that
  synchronous call. Native dismountTo performs the existing passenger move.
  The temporary point clears even if another native hook cancels dismount.
* Band selection/ending and disabled-resident cleanup respect a blocked exit.
  Existing explicit recovery refuses if this exit is blocked; its other gates
  and behavior are unchanged. No recovery was executed by this source work.
* Expose seat_dismounts and seat_dismount_waits counters for the next real trial.

The guard covers this adapter's voluntary activity transitions. Other forced
native removal/dismount paths retain Handcrafted's behavior. No generic entity
teleport, graph expansion, world edit, ledger reset or render context is added.

## Pinned API proof and checks

Actual pinned Minecraft1.21.1 bytecode shows LivingEntity.stopRiding retaining
the original vehicle, calling Entity.stopRiding, and only after actual server
detachment invoking dismountVehicle(originalVehicle). That calls the vehicle's
public getDismountLocationForPassenger and native dismountTo. The pinned
Handcrafted4.0.3 implementation uses the same public DismountHelper API, the
same0.25 lift, and otherwise falls back to the generic vehicle location.

The complete proposed adapter compiles with Java21 against the pinned APIs.
Fourteen focused scenarios execute the actual ManagedSeat source and extracted,
unchanged copies of the proposed reservation/stand/destination methods against
explicit simulated native boundaries. They cover a clear exit, block/living
collision, reservations, missing chunks, unadmitted approach, changed chair,
missing floor, wrong height, wrong owner, cancelled native dismount, containment,
ordinary retry and ordinary walking. They are safety-logic evidence, not a game
session. Two focused Python roster/dashboard tests also pass.

The first fixture used a boundary cell whose center was actually inside the
approved footprint. The corrected fixture uses a cell outside it; the initial
failed fixture output remains private alongside the validated run. Production
code did not change to satisfy that incorrect expectation.

Review material is under
`D:\A World for Two\staging\drowned-rose-source-20261029\dismount-0111-review`:
before-source copies/hashes, SAFE-DISMOUNT.diff, compiler output, exact native
API excerpts and the bounded fixture source/output. Real validation must show
waiting when occupied, eventual dismount to the admitted approach, no new stacks,
and seat/passenger reload survival. No such runtime success is claimed here.
