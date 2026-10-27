# MapHorizons: read-only SeedGen LOD adapter candidate

This source-only candidate extends the selected MapHorizons renderer to read existing Distant Horizons terrain at its stored resolution. It generates no terrain, marks no chunk explored, writes no Xaero discovery data and introduces no new map renderer or minimap. No mod JAR, installed instance, Packwiz pin or server setting is changed by this source checkpoint.

## Findings in the previous experiment

The installed MapHorizons `1.1.0-awft.1` indexes only DH section-detail 6: 64×64-block sections at block resolution. The earlier untracked refresh recipe also selected only database `DetailLevel=0`, so refreshing it would still omit coarse SeedGen LODs. The actual pinned SeedGen 0.9.1 exposes a range of data resolutions; some of its distant output therefore cannot be assumed to exist at block resolution.

DH 3.3.3's `getAllPositions()` exists and correctly translates database detail to section detail by adding 6. This was not a missing-API defect. The database coordinate/detail contract is also documented in the [pinned DH repository source](https://gitlab.com/distant-horizons-team/distant-horizons-core/-/blob/3.3.3/core/src/main/java/com/seibel/distanthorizons/core/sql/repo/FullDataSourceV2Repo.java).

The earlier reader used `jdbc:sqlite:`. Actual pinned-driver execution failed with no suitable driver: DH shades its driver as `dh_sqlite.JDBC` and accepts `jdbc:dh_sqlite:`. The corrected reader has been exercised against that exact bundled driver, including refusal of an attempted write through its read-only connection. The earlier validation also checked SQL null only after reading Z and used an overflow-prone absolute-value check; null X, `Long.MIN_VALUE` and fractional coordinates now fail explicitly.

A database snapshot could previously replace an index after a listener added a newer section. The new provider-owned lease retains a bounded overlay of not-yet-persisted observations when publishing a scan. Detached/replaced providers invalidate their leases; queued cache invalidation checks its attachment identity on the client thread.

Original untracked bytes were preserved privately before edits in a create-once archive with individual file hashes. Compiler/probe failures remain alongside the later passing receipts. Those private files contain no public acceptance authority.

## Integration

`LodCoverage.java` is original interoperability code. It indexes real native source coordinates at database details **0–12**, chooses the finest indexed source covering a requested 64-block render rectangle, and groups at most 64 target rectangles for one 512-block map region. It does not expand a huge coarse source into a fictitious collection of native leaf LODs or loaded chunks. Negative coordinates use floor division. Coordinates beyond Minecraft's supported range are rejected/clipped.

`tools.maphorizons_refresh.changed_source()` and `changed_regions()` require the exact reviewed author-source hashes. The recipe keeps the existing MapHorizons color, height, biome, water and Nether-floor renderer, adapting its sampling coordinates to the native source scale. Repeated output pixels reuse the same parsed native column. Coarse colors remain coarse; no higher-resolution detail is fabricated. The region callback refreshes only cached regions touched by a source, rather than iterating a huge coarse extent.

The metadata scan runs on MapHorizons' existing background worker, selects positions only, and uses a read-only connection. It is capped at 262,144 sources; the pending overlay is capped at 4,096. A new scan starts no sooner than 30 seconds after the preceding scan completes. The row loop has a 250 ms work deadline and JDBC's query timeout is one second; these are work/driver limits, not a guarantee that every filesystem operation completes within 250 ms. Failure retains the previous index. Unsupported data detail above 12 remains absent.

Rendering still reads native DTOs via `repo.getByKey`, avoiding DH's request-on-load path. An indexed source that is empty, unavailable or undecodable remains a hole/retry, including when a finer indexed placeholder covers a valid coarser source. No additional section sharing, seed lookup or full-chunk generation is added.

## Authority and fidelity

The existing `TerrainHighlighter`, `ExploredClient`, server exploration tracking, sharing protocol and party-source code are unchanged. Their server-provided visibility mask is still checked when Xaero requests a chunk's colors. Real Xaero mapping retains precedence, and claim overlays remain above this terrain highlight. See [MapHorizons' architecture and limits](https://github.com/VolcanicMG/MapHorizons/blob/6c80ad5be5fff2c373388dfd6ff433667edd7217/README.md).

The inspected server configuration currently permits a full atlas (`teamScoped=false`, `showUnexploredTerrain=true`). MapHorizons supports **FTB Teams**, not Open Parties and Claims party membership. This adapter grants no new party authority and makes no OPAC privacy claim. Any future OPAC restriction must be enforced through a reviewed server integration. Map masking is not a security boundary for LODs already available in DH's separate 3D view.

SeedGen terrain is a prediction and can approximate vegetation/features. Successful registry/fingerprint validation does not establish exact block or structure fidelity, and this lane does not assume the parent's current strict-parity test passed. This adapter reads only whatever valid native LOD data already exists; it cannot repair missing generation, a SeedGen refusal, absent server data or inaccurate predictions. See the [author's SeedGen description](https://modrinth.com/mod/distant-horizons-seedgen). No SeedGen source or artifact is modified or copied into this candidate.

## Evidence and remaining gates

The original helper fixtures now cover coarse/fine precedence, negative-coordinate projection, bounded grouping without leaf expansion, parsed-column reuse and null holes, stale-scan races, provider invalidation, one refresh lease, real read-only JDBC behavior and invalid-coordinate rejection. Standalone tests use Java 21 / 64 MiB / two processors and temporary fixture databases only. The generated changed classes also compile against actual pinned MapHorizons, DH 3.3.3, Xaero World Map 1.47.0 and Minecraft 1.21.1 client APIs, with no game startup or JAR packaging. Those checks prove arithmetic, JDBC behavior and class linkage; **actual map rendering and performance are unverified**.

A native acceptance pass must show all of the following on an owned test instance:

1. With server visibility explicitly allowing it, a region containing valid coarse SeedGen/DH source data appears on Xaero's World Map before real client chunks are received there. Compare known sample coordinates/resolutions with the actual native source and retain before/after views.
2. Genuine mapped terrain takes precedence after visiting the area; no synthetic exploration bit or full chunk was created merely by opening the map. Xaero's Minimap can reuse the same appearance when its normal world-map-chunk mode is enabled.
3. A denied region remains denied under an actual server-supported policy. Party claims from OPAC alone do not prove such a policy exists. Validate claims as overlays separately.
4. Overworld, Nether and End, disconnect/reconnect and dimension/provider changes show no stale data from another attachment. Empty/corrupt/unavailable sources remain honest holes.
5. Measure map-open frame times, CPU, RAM, queue/scan times and refresh behavior while generation proceeds. No overhead number or remote two-player acceptance is supplied by the standalone fixtures.

`tools.maphorizons_refresh.apply(fresh_author_tree)` stages the exact recipe and helper sources only. The author tree must be the pinned commit and must have no prior refresh helpers. Compilation/probes, packaging a new artifact, changing pins and native validation remain separately authorized steps. Preserve the MIT license and notice in any derived MapHorizons artifact.
