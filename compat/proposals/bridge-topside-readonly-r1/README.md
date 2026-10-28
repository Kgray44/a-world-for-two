# Retain the existing working bridge glue

Original optional candidate46 source proposal. No active Java source, build or
world was changed by its author. Parent must compile/API-review and integrate it.

Construct `RetainedBridgeGlueInspection(candidate, bridge, sharedInterlock)`;
register its commands, call `tick` on the server tick and `stop` on server stop,
and include `busy()` in the existing shared maintenance admission. Reuse the
installed `RefinementGlueAdmission.canonical` typed-NBT encoder; never invoke its
retirement command. Add only the typed local-console `awftbridgetop inspect`
confirmation path. The operation is inspect-only.

The private request format is `awft-retained-bridge-inspection:1`. Bind actual
`candidate`, `bridge`, `pack_sha256`, `native_class_sha256` and exact file refs
(`path` home-relative, `bytes`, `sha256`) for `checkpoint`, `census`, `preimage`,
`native_before`, `native_before_complete`, `north_original`, `south_original`.
The census/preimage come from a fresh run of the saved-glue source producer at
the CURRENT stopped checkpoint. The original53+53 deltas remain the frozen
forbidden plans and are pinned by exact SHA. The actual current106 native BEFORE
must be clean, complete and younger than300seconds. Do not create a fake receipt.

Write a NEW `dashboard/settlement/bridge-topside-inspection-<requestsha16>/request.json`.
The parent may then confirm `awftbridgetop inspect <bundle> <fullsha>` locally.
This takes one shared empty-world lease, temporary tickets for at most16 existing
bridge chunks, queues FULL with generation disabled, and wakes simulation only
within its explicit600tick window. It waits for actual FULL/entity/kinetic and
closed-controller readiness. A failed release/pending shared future retains the
cleanup gate and needs explicit cancel cleanup; no shared future is cancelled.

The actual inspection checks both saved UUIDs, exact live SuperGlueEntity class,
complete typed persistent NBT/hash, AABB, life/passenger state, strict current106
block states, no extra loaded glue and no interfering passenger/contraption. The
snapshot census is complete for authenticated saved regions; live inventory is
explicitly the loaded native stage, with both reviewed UUIDs concretely resolved.
It does not force-load the whole world or infer unloaded entities are absent.

The two existing glue boxes contain all106 proposed whole voxels. Therefore
retirement/setup/regluing is not justified by this alteration. After the parent
obtains real custody and physically admits the exact additions, full bridge
verification precedes COMMISSION ONLY. Actual EngineeringSupport phase0 performs
setup/glue creation/radio programming only for mode `setup`; `commission` checks
the existing closed mechanism then uses real bank buttons for two55degree cycles.
Afterward normal Create disassembly can replace glue UUIDs, so save a fresh census
and verify restart using new actual identities. Walking, appearance and
vessel-specific clearance remain separate from this read-only proof.

No command in this proposal places a block, edits NBT, moves/discards/spawns an
entity, changes a sequencer, creates glue, pulses a button or grants motion.
