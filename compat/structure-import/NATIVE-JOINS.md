# Real-level native join proposal

`NativeImportJoins.java` deliberately lives outside active bridge sources. Parent
integration and the next candidate build are required before it can run. It is
not a standalone Java renderer, fake Level or bootstrap-based connection model.

The proposal compiles with the actual installed NeoForge 21.1.262 API, named
Minecraft 1.21.1 API and existing bridge interface. That compile is API evidence
only. No native server operation or world change was performed by this lane.

Parent wiring consists of a `NativeImportJoins` field with the exact candidate
and bridge versions plus `this::acquire`, a command listener, its server tick
hook, and `stopped()` in the existing before-level-close shutdown path. The class
uses `ArtisticEngineeringSupport.Interlock/Lease`; the existing `WorldLease`
already implements the required interface. The shared operation owner blocks
SettlementSupport and the other maintenance helpers until cleanup completes.
Do not start another world operation while a shared future or ticket cleanup is
pending. No broad changes to existing construction or admission policy are needed.

Only the two frozen original adaptations are accepted, by exact original plan
and preimage hashes and exact addressed target counts, 4,406 or 2,252. Source
geometry, materials, supplied properties, literal tags and commands cannot be
rewritten. Fresh active placement/preimage copies may change only the checkpoint
SHA. The helper requires the current canonical verified checkpoint receipt,
matching actual world path/seed, owned artistic-stage marker and home, port25575,
empty server, actual installed/active candidate agreement, exact running bridge
version and the actual loaded helper class hash. Fresh completed before/placement
receipts must bind the exact active plans in chronological order.

`prepare_native_joins.py` creates the small immutable request after those parent
native actions. Pass `--home`, frozen `--source` directory, `--kind tavern|shop`,
`--before-proof`, `--placement-proof`, the installed `--bridge-jar`, exact
`--candidate` and `--bridge-version`. Optional `--plan` and `--preimage` identify
checkpoint-only rebound copies. The tool obtains the self-class hash directly
from the actual candidate JAR. It returns a console command but never executes it.

For each original, perform this sequence:

1. Verify its exact native saved preimage and preserve the immutable receipt.
2. Place the exact addressed adaptation once and preserve the placement receipt.
3. Create and review the immutable request, then invoke `awftimport settle` with
   its bundle name and exact hash. The command is console-only at permission4.
4. Wait for an immutable `import-joins-result-...json` with `failures:0`, no
   `error`, `cleanup:"complete"`, `strict_all_state_verification:true`, and
   `all_native_be_inventory_equality:true`. An export file's `.complete` marker
   means only that its bytes finished writing; it is not verification acceptance.
5. Inspect the actual exported complete states/tags and verify the new
   `import-verify-only-...json` through the unchanged settlement verifier as an
   additional check. Never place this export or replay its inventory data.
6. Inspect actual game/shader views, doors, stairs, supports, windows, profiles
   and routes. Native state agreement does not establish artistic acceptance.

Within the existing lease, the helper loads only generated chunks around the
exact addressed originals and one-block read neighborhood. At most32 chunks and
1,200 ticks are admitted. It performs at most128 addressed operations or4ms of
work per tick. Three normal `Block.updateFromNeighbourShapes` passes use the
actual live level and loaded tags; changed states go through `setBlock(...,3)`
and native neighbor notifications. There is no source-state replay, source
command execution, entity spawn or blanket rectangular fill. Every originally
supplied property is checked before and after normal updates. Unexpected lost
identities or changed structural intent cause failure rather than normalization.

All actual addressed block-entity NBT and inventories are captured before joins
and must remain equal afterward, including default furnishings absent from old
source NBT. Authored literal profiles/patterns are checked as supplied. After
convergence and20 native ticks, complete actual BlockStates and native block
entity tags are exported. Another20 ticks later, the helper independently checks
every complete state and all those native tags again. No final state property is
omitted. A successful file is explicitly labelled verification-only and retains
the original input provenance in the terminal request/plan hashes.

Own tickets are removed on every terminal path. Shared Minecraft futures are
never cancelled or treated as stopped merely because a ticket was released. The
lease remains held until cleanup is complete; an interrupted/failed attempt gets
an immutable receipt even when cleanup remains pending. Partial native effects
remain for explicit review and backup recovery. Restart never silently resumes.
The output bound is8MiB per actual-state export plus a small immutable receipt;
the parent must apply ReserveGuard before the native writer. That monitoring does
not constrain external applications or writers that have not loaded the rule.
