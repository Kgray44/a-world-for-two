# SeedGen: current runtime gap

## Observed candidate.29 and candidate.30 results

Actual dedicated-server logins with matching candidate.29 and candidate.30 clients
succeeded, but SeedGen's strict terrain fingerprint comparison still failed with
the same values:

| Native comparison | Value |
| --- | --- |
| Server fingerprint | `de19e29860fac400` |
| Client fingerprint | `39421890d93f9c73` |
| Reported missing entries | None |
| Reported extra entries | None |

Both sides receive the same cinematic datapack through Packwiz/Paxi. That delivery
did **not** establish matching terrain fingerprints. An equal entry-name set does
not prove equal registered content or selected data-pack resources. SeedGen's
strict checks remain enabled; remote terrain agreement and faithful SeedGen LOD
generation are unqualified for this candidate.

## Corrected load-order defect and remaining candidate.31 gap

Tectonic 3.0.28 stores terrain data in `resourcepacks/tectonic`. Actual candidate.30
inspection found that native pack **already present** in the client repository.
The earlier missing-pack diagnosis was incorrect; its adapter did not establish
parity. The observed gap is load order: the client opened Tectonic before raw mod
roots, so later Terralith resources overrode 16 conflicting entries. The dedicated
server selected Tectonic after `mod_data` instead.

The candidate.31 client-only correction reuses the exact existing Tectonic
`PackResources`, removing and reappending it after raw mod roots and before
explicit extras. Original metadata and conditional overlays remain attached to
that resource object. Admission retains the pinned original version,
451,757-byte artifact and SHA-512. No terrain assets are copied and no fingerprint
code changes. Earlier fixture compilation/table checks do not establish the
corrected order's actual native result.

The actual candidate.31 login at **11:20:30–33 UTC** confirmed the existing pack
moving from index **232 to 374**. The client fingerprint changed, but parity still
failed:

| Candidate.31 native comparison | Value |
| --- | --- |
| Server fingerprint | `de19e29860fac400` |
| Client fingerprint | `f2fed434d47f6565` |
| Strict client terrain generation | Rejected; remains off |

This confirms a real ordering correction, not a complete terrain repair. Another
registered-content difference remains unresolved. Distant Horizons server-download
fallback is retained. No further adapter change or permissive fingerprint bypass
is selected, and no faithful client SeedGen LOD-generation claim is made.

## One bounded shutdown trial

The Distant Horizons background fallback was tested with
`chunkGeneratorMode = "SURFACE"`, retaining `SURFACE_THEN_CHUNKS`. After roughly
four minutes with one client, the actual JVM shut down normally at
**2026-10-27 11:00:53 UTC**, with no orphan JVM left behind.

This is one observed clean shutdown under the narrower fallback setting. It is
not repeated shutdown/reconnect acceptance, a fix for the SeedGen mismatch, a
terrain-arrival benchmark or proof of long-running background-generation safety.
The trial does not identify the fingerprint mismatch's cause.

SURFACE limits the fallback's feature/decorative generation; distant terrain may
therefore lack decoration that appears in full player-driven chunks. The normal
player-driven world-generation path retains its features. Distant Horizons and
SeedGen remain selected, with Voxy and Roxy excluded.

## Checks still required

- Verify the selected built-in terrain pack's priority through the narrow adapter,
  without relaxing the comparison or replacing its original metadata/overlays.
- Diagnose the remaining registered-content difference; the actual candidate.31
  paired test is complete and failed strict agreement.
- Separately exercise background LOD generation, travel, reconnect and repeated
  normal shutdown, and measure terrain arrival and resource cost.
- Retain the mismatch and shutdown receipts. Do not reinterpret the one clean
  trial as full distant-terrain or multiplayer acceptance.

See [current release status](STATUS.md) and [cinematic coverage limits](SETTLEMENT-CINEMATIC.md).
