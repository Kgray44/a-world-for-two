# Existing Native temporary-read handoff for empty-server initialization

Source only: no command was executed by this chat. Root remains sole operator.

The installed9722 adapter requires four loaded chunks:

| Chunk X/Z | Exact adapter anchor X/Y/Z |
| --- | --- |
|80 /−81 |1280 /65 /−1296 |
|80 /−80 |1280 /65 /−1280 |
|81 /−81 |1296 /65 /−1296 |
|81 /−80 |1296 /65 /−1280 |

Prepared plan:
`D:\A World for Two\staging\drowned-rose-source-20261029\native-warm-19cdc3\TAVERN2916-VERIFY-ONLY.json`

SHA256 `2196688322333ef699469047fc06c72877cf3dee2d92c1088d18acba616cbc05`;
59,513bytes,2,916 unique block-state reads,0 block-entity tag rows,0 commands,
`construction_forbidden=true`, `verification_only=true`. Never PLACE or SETTLE it.

The immutable preimage source is19cdc3
(`20261030T005523Z-19cdc3`, SHA256
`8ecd665c23a4a6e91d2132d79cb528d274050b7a3e051de5c4ecd06016c78922`).
Every saved field cell matches the actual installedb296 config. The16 chunks
in the union of Native's radius-one neighborhoods are authenticated saved FULL;
no new generation is needed. Exact source/hash/anchor facts are recorded in
the adjacent `MANIFEST.json`.

The current Native admission receipt still names canonical6ad3. The plan's
`backup_sha256` correctly uses that actual admission receipt; the newer19cdc3
source checkpoint is separately recorded. Do not rewrite custody pointers or
claim canonical6ad3 is the latest saved population checkpoint.

Use the existing serialized `tools.artistic_review.native` mechanism for this
one VERIFY. It checks current empty roster, actual server identity, exact plan
hash, canonical receipt and genuine terminal/cleanup. After its successful
return, Root can immediately send:

```text
awfttavern initialize b2963d58e4dd14e542c24e2b926ddb76ead1a3a7b627a951a2fb348ca85929a4
```

Initialization itself repeats loaded-chunk and exact full-state preimage checks;
an additional inspect command between verification and initialization adds delay
without avoiding a check. A loaded-chunk refusal happens before any NPC creation.
Read and retain the actual result; do not assume the attempt succeeded.

## Timing facts and bounded fallback

Existing SettlementSupport processes at most192 rows or4ms per tick; the2,916
reads therefore require at least16 work ticks, plus native FULL readiness. This
is a source-derived bound, not a measured elapsed time. The read order is grouped
by the four actual chunks, ending at1310,72,−1271, center81/−80. Every one of the
four possible radius-one3×3 centers covers all four tavern chunks. Native queues
nine FULL futures at a time, not six; the four-center union is16 saved chunks.

`finish()` synchronously calls `removeRegionTicket`, then writes the genuine
terminal and marks idle. Minecraft may subsequently unload chunks. There is no
guaranteed post-terminal retention window, and a successful VERIFY is not a
promise that a later `hasChunkAt` will pass.

If the immediate post-terminal attempt actually refuses because chunks have
unloaded, Root can use the same finite read operation with an in-flight handoff:

1. Start one existing VERIFY, with no competing Native block writer.
2. Read its actual in-memory report using existing `awftbuild status`, bounded
   to20 status requests100ms apart. Observe matching plan SHA, `phase=0`,
   `cursor>0`, `failures=0`, unfinished. This proves a Native FULL neighborhood
   was acquired and its read operation is still active. Do not infer readiness
   from elapsed time or a stale status file: file progress is written only every
   five seconds and this operation may finish sooner.
3. Immediately queue exactly one hash-bound initialize on that observed state.
   The Native operation only reads block states; initialization independently
   checks all2,916 exact states and every missing resident's free body before insertion.
   Both run serially on the server thread under the sole Root operator.
4. Retain the Native terminal and require0 failures,0 temporary tickets and no
   cleanup requirement. Verify actual tavern registration/UUID counts separately.

If that observation window is missed, it is not evidence that initialization
occurred or that chunks are still resident. Do not pad the plan with hundreds
of thousands of repeated reads, set world spawn, add permanent force-loads, hold
new tickets, create another world, or claim a new JAR/restart is required without
an observed failure.

With no nearby player, successfully inserted patrons are intentionally dormant;
population presence/registration is separate from visible walking, seating and
native musical playback. Those need the later owner-permitted client session.
