# Bounded native fountain reset proposal

This is an isolated replacement and patch for `NativeFountainSupport.java`.
The active source, runtime and world were not changed. The exact source base is
`cab045da9c7851507fd9bbd6ba4611550dcf70c53080f7f2d5e6b434e07ab656`.
Preserve the exact private D:/world-tests and RosewaterArtistic path guards when
integrating. A source-base mismatch requires review rather than blind overwrite.

The proposal adds the console-only `awftfountain reset <bundle> <request-sha>` to
the existing fountain command. The parent must also admit this private typed
action in its controller allowlist. Existing inspect/commission admission and
hydraulic branches remain. No reset runs during construction, startup or reload.

Request format remains `awft-native-fountain:1`, with the same exact candidate,
bridge, pack SHA, seed, world path, checkpoint SHA and actual installed fountain
class SHA. It additionally requires these hash/size/home-relative-path references:

- `reset_manifest`: frozen wet bundle manifest SHA256
  `f1bc94aa5397f3f7dd97eb086a8b7cd3c35f996a73e16a14407f9cb7c8fcf3ac`.
- `reset_before`: three references, ordered wheel source, owned pumped header,
  then lever/diode. They must match the manifest's exact before files.
- `reset_native_verify`: three matching **actual**, fresh successful native
  settlement verification receipts and authentic completion markers. Each must
  bind the corresponding before SHA and exact1/1/2 counts, with zero failures,
  cleanup, tickets and futures. Their native journal origin and30minute age are
  checked. No proof or request was fabricated by this proposal.

The source bundle is
`staging/artistic-fountain-centerpiece-r5-wet-reset-20261027T2255Z` and its current
checkpoint is b8495b677653c31077036faad10f553b432dcb173cd8964c8bb48e4674bd35f7.
The three before files are `reset-1-wheel-off-BEFORE.json`,
`reset-2-owned-header-off-BEFORE.json`, `reset-3-normal-controls-BEFORE.json`.
Run ordinary strict native verify on those current wet states before preparing
the reset request. The helper also compares every state again under its exclusive
lease, then rechecks each phase's exact before immediately before mutation.

The admitted operations are fixed in code, not supplied as arbitrary targets:

1. Remove only the independently seeded wheel source at1145,69,−1131 through
   `setBlock(AIR,3)` and normal neighbor notification. Wait for actual wheel and
   pump0RPM for40stable ticks.
2. Recheck the actual owned pumped header source at1138,73,−1129. Remove only
   that source normally, then wait for normal downstream AIR at the header,
   port and four jet witnesses, with zero drive for40stable ticks.
3. Recheck original levertrue/NORTH diode. Apply ordinary leverfalse and change
   only the repeater facing SOUTH. Wait for dry core, zero drive, actual piston
   retraction, original quartz plug return, unpowered corrected controls and
   retained intake source for40stable ticks.

The existing shared maintenance interlock, FULL ticking tickets and lifecycle
cleanup are reused. `resetEmptyTime` is called only inside the explicitly active
reset lease, bounded by1800server ticks. Phase budgets are600/600/400ticks. There
are no fake players, source/flow NBT writes, manual kinetic speeds, blanket fluid
clearing, piston/plug writes, inventory mutation, geometry replay or automatic
retry/rollback. Failure/cancellation preserves actual partial world state and
publishes cleanup custody; outstanding shared futures retain the lease until
cleanup can finish. Inspect still does not reset the empty timer.

After actual reset success, stop normally and create a **fresh stopped dry
checkpoint**. The frozen fountain producer's `--dry-checkpoint` mode must derive
actual saved preimages before R5 art placement. This reset is recovery evidence,
not pumped commissioning, restart persistence or visual acceptance.

The isolated proposal compiled against the actual42 installed bridge, named
Minecraft/NeoForge APIs and pinned Create6.0.10 APIs. The initial missing-Ponder
compile is retained; adding the genuine pinned nested compile dependencies
resolved it. No fake Level or world simulation was used. Compile evidence is
private under `H/staging/fountain-reset-native-compile-20261027T2302Z`.
